import json, time, random
from loguru import logger
from datetime import datetime
from requests.api import head
from taxes.utils import fill_pdf
from aws import save_to_s3
import os

# expense categories, these are lists of keys of the dict keys in the expense dict in tax_data col in db table
# the map is in the reformat.json file in hnttax_form_fetch/config
# SUPPLIES_EXPENSES = ["hotspot", "outdoor_bundle_kits", "antenna", "poe_injector", "coax_cable", 
#                     "grounding_equipment", "ethernet_cables", "solar_equipment", "other_equipment",
#                     "hardware_wallet", "validator_equipment"
#                    ]
SUPPLIES_EXPENSES = []

# all supplies are now going to PART 5 OTHER EXPENSES - but commenting above in case we return to that
PART_5_OTHER = ["hotspot", "outdoor_bundle_kits", "antenna", "poe_injector", "coax_cable",
                "grounding_equipment", "ethernet_cables", "solar_equipment", "other_equipment",
                "hardware_wallet", "validator_equipment"
                ]

UTILITIES_EXPENSES = ["internet", "cell_phone", "validator_utilities"]

LABOR_EXPENSES = ["professional_install"]

TRAVEL_EXPENSES = ["travel"]

BUSINESS_EXPENSES = ["business_property"]

OFFICE_EXPENSES = ["office_expenses"]

# 2021 mileage rate 
MILEAGE_RATE = 0.56


def write_data_to_1040(output_filename, data, tax_year):
    """
    Writes data dict to output_filename provided, overlaying the 1040 schedule c form
    """
    pdf_file = f"tax_forms/f1040sc_{tax_year}.pdf"
    key_file = f"tax_forms/f1040sc_{tax_year}_key.json"
    output_file = "output/" + output_filename

    pdf_keys = json.load(open(key_file, 'r'))
    
    # Build fillable data to input to pdf filler fn
    fillable_data = {}
    for key, value in pdf_keys.items():
        if key in data.keys():
            # if this is an amount, check if > 0
            if (type(data[key]) == int or type(data[key]) == float) and data[key] == 0:
                continue

            fillable_data[value] = data[key]

    logger.info(f"Saving completed 1040 schedule c for to: {output_file}")
    fill_pdf(pdf_file, output_file, fillable_data)
    return output_file


def write_data_to_txf(filename, tax_data):
    """
    Takes in tax_data dict used to write to pdf, creates a txf file and saves locally
    Returns local filename 
    """
    output_file = "output/" + filename
    key_file = "tax_forms/txf_key.json"

    pdf_keys = json.load(open(key_file, 'r'))
    todays_date = datetime.today().strftime('%m-%d-%Y')

    with open(output_file, 'w') as txf:
        # add header to output file
        header_fields = ["V042\n", "AhntTax TXF Software\n", f"{todays_date}\n", "^\n"]
        txf.writelines(header_fields)

        # add descriptive fields 
        for key, amt in tax_data.items():
            if key in pdf_keys.keys():
                # use key of this item in tax_data to access map details for txf
                descriptors = pdf_keys[key]["descriptors"]
                txf.writelines(descriptors)

                # If this is of type = expense, we want valu to be negative
                item_type = pdf_keys[key]["type"]
                if item_type == "expense" and amt > 0:
                    txf.write(f"$-{amt}\n")
                else:
                    # Add amount to next line
                    txf.write(f"${amt}\n")

                # add carrot to separate sections
                txf.write("^\n")
    
    return output_file



def write_schc(income, input_json, dbid):
    """
    Takes in input data in json format, calls get_helium_rewards and performs steps to fill pdf
    """
    # validation - if no income, set to 0
    if income is None:
        income = 0
    else:
        income = int(income)
    
    # handle the non-computed fields
    name = input_json['name']
    tax_year = input_json['tax_year']

    logger.info(f"Preparing {tax_year} Schedule C form for: {name}")

    # build input pdf data as we go
    tax_data = {
        "name of proprietor": name,
    }

    # handle the static (always the same for all clients) fields
    tax_data['A'] = "Cryptocurrency mining"
    tax_data['B'] = "523900"
    tax_data['F1'] = True
    tax_data['G-Y'] = True
    
    tax_data['1-line'] = income
    tax_data['7'] = income

    # Sum up all expenses - first get them from the input json tax_data dict from db
    expenses = input_json['expenses']

    supplies_expenses = 0
    utilities_expense = 0
    contract_labor = 0
    invoice_labor = 0
    travel_costs = 0
    travel_meals = 0
    business_property_exp = 0
    office_expenses = 0
    part5_expenses = 0
    usd_hosts_paid = 0
    # loop through expenses dict in tax_data col in db table
    for exp_type, expense_info in expenses.items():
        # if there is a cost associated, and the cost is not an empty string/falsy
        if "cost" in expense_info and expense_info['cost']:
            exp_amt = float(expense_info['cost'])
        
            # get expenses that fall under "part 5 other" (we used to put these to supplies line) 
            if exp_type in PART_5_OTHER:
                part5_expenses += exp_amt
        
            # get expenses that fall under "utilities"
            if exp_type in UTILITIES_EXPENSES:
                utilities_expense += exp_amt

            # get labor expenses
            if exp_type in LABOR_EXPENSES:
                if expense_info['type'] == 'Independent contractor':
                    contract_labor += exp_amt
                if expense_info['type'] == 'Received invoice from company':
                    invoice_labor += exp_amt
                else:
                    logger.warning(f"Invalid expense type for labor: {expense_info['type']}")

            # get business property expenses
            if exp_type in BUSINESS_EXPENSES:
                business_property_exp += exp_amt

            # get office expenses
            if exp_type in OFFICE_EXPENSES:
                office_expenses += exp_amt
            
            logger.debug(f"Expense: {exp_type} --> Amount: ${exp_amt}")

        # get travel expenses - separate bc multiple 'cost' values in dict
        if exp_type in TRAVEL_EXPENSES:
            if expense_info['miles_traveled']:
                miles_traveled_cost = MILEAGE_RATE * float(expense_info['miles_traveled'])
                travel_costs += miles_traveled_cost
                logger.debug(f"Expense: {exp_type} miles_traveled --> Amount: ${miles_traveled_cost}")
            
            if expense_info['travel_cost']:
                travel_costs += float(expense_info['travel_cost'])
                logger.debug(f"Expense: {exp_type} travel_cost --> Amount: ${expense_info['travel_cost']}")
            
            if expense_info['meals_cost']:
                travel_meals += float(expense_info['meals_cost'])
                logger.debug(f"Expense: {exp_type} meals_cost --> Amount: ${expense_info['meals_cost']}")

        # get usd paid to any hosts, only if paid in USD
        if exp_type == 'hosting':
            if expense_info['payment_currency'] == 'USD':
                contract_labor += float(expense_info['usd_paid'])
                logger.debug(f"Expense: {exp_type} --> Amount: ${expense_info['usd_paid']}")
            elif expense_info['payment_currency'] == 'HNT':
                logger.warning(f"Host paid in non-USD currency (id: {dbid} - {name}, {tax_year})")

    # PART 2 - now that we have all expenses organized - categorize to schc fields
    # Sum together claimable expenses for reporting, add to pdf data 
    tax_data['11'] = int(contract_labor)
    tax_data['18'] = int(office_expenses)
    tax_data['20b'] = int(business_property_exp)
    tax_data['22'] = int(supplies_expenses)
    tax_data['24a'] = int(travel_costs)
    tax_data['24b'] = int(travel_meals)
    tax_data['25'] = int(utilities_expense)

    # if part5 expesnes, write them to the entry/amt lines
    part5_sum = 0
    if part5_expenses:
        tax_data['part5-expense-entry'] = "Miscellaneous equipment"
        tax_data['part5-expense-amt'] = int(part5_expenses)
        part5_sum += int(part5_expenses)

    # other expenses - add invoice labor here
    if invoice_labor:
        tax_data['part5-entry-2'] = "Professional installation"
        tax_data['part5-amt-2'] = int(invoice_labor)
        part5_sum += int(invoice_labor)

    # if we had any part 5 expenses at this point, write them to the total fields and field 27a
    if part5_sum:    
        tax_data['part5-other-expenses-sum'] = part5_sum
        tax_data['27a'] = part5_sum

    # sum these up for total 
    expenses_claim_sum = contract_labor + office_expenses + business_property_exp + supplies_expenses + travel_meals + travel_costs + utilities_expense + part5_sum
    tax_data['28'] = int(expenses_claim_sum)
    logger.info(f"Sum of all claimable expenses: ${expenses_claim_sum}")

    # Subtract expense from rewards
    net_profit = income - expenses_claim_sum
    logger.info(f"Total taxable earnings for year {tax_year}: ${net_profit}")
    tax_data['31'] = int(net_profit)

    # Write tax_data to pdf 
    name_no_space = name.replace(" ", "_")
    output_pdf = f"{name_no_space}_{tax_year}_1040sc.pdf"
    logger.debug(f"Input dict for tax form: {tax_data}")
    local_pdf_file = write_data_to_1040(output_pdf, tax_data, tax_year)

    # save schedule c pdf to aws s3
    aws_filename = f"{dbid}/{output_pdf}"
    save_to_s3(local_pdf_file, file_year=tax_year, aws_file_name=aws_filename)

    # Write tax data to txf file
    output_txf = f"{name_no_space}_{tax_year}_1040sc.txf"
    local_txf_file = write_data_to_txf(output_txf, tax_data)

    # save txf to aws s3
    aws_txf_filename = f"{dbid}/{output_txf}"
    save_to_s3(local_txf_file, file_year=tax_year, aws_file_name=aws_txf_filename)

    # delete local file versions of sch c and txf
    os.remove(local_pdf_file)
    os.remove(local_txf_file)
