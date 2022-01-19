import json, time, random
from loguru import logger

from requests.api import head
from taxes.utils import fill_pdf
from aws import save_1040_to_s3
import os

# expense categories, these are lists of keys of the dict keys in the expense dict in tax_data col in db table
# the map is in the reformat.json file in hnttax_form_fetch/config
SUPPLIES_EXPENSES = ["hotspot", "outdoor_bundle_kits", "antenna", "poe_injector", "coax_cable", 
                     "grounding_equipment", "ethernet_cables", "solar_equipment", "other_equipment",
                     "hardware_wallet", "validator_equipment"
                    ]

UTILITIES_EXPENSES = ["internet", "cell_phone", "validator_utilities"]

LABOR_EXPENSES = ["professional_install"]

TRAVEL_EXPENSES = ["travel"]

BUSINESS_EXPENSES = ["business_property"]

OFFICE_EXPENSES = ["office_expenses"]

# 2020 mileage rate 
MILEAGE_RATE = 0.575


def write_data_to_1040(output_filename, data):
    """
    Writes data dict to output_filename provided, overlaying the 1040 schedule c form
    """
    pdf_file = "tax_forms/f1040sc.pdf"
    key_file = "tax_forms/f1040sc_key.json"
    output_file = "output/" + output_filename

    pdf_keys = json.load(open(key_file, 'r'))
    
    # Build fillable data to input to pdf filler fn
    fillable_data = {}
    for key, value in pdf_keys.items():
        if key in data.keys():
            fillable_data[value] = data[key]

    logger.info(f"Saving completed 1040 schedule c for to: {output_file}")
    fill_pdf(pdf_file, output_file, fillable_data)
    return output_file


def write_schc(income, input_json, dbid):
    """
    Takes in input data in json format, calls get_helium_rewards and performs steps to fill pdf
    """
    name = input_json['name']
    tax_year = input_json['tax_year']

    logger.info(f"Preparing {tax_year} Schedule C form for: {name}")


    # build input pdf data as we go
    tax_data = {
        "name of proprietor": name,
    }

    tax_data['1-line'] = income
    tax_data['7'] = income

    # Sum up all expenses
    expenses = input_json['expenses']

    supplies_expenses = 0
    utilities_expense = 0
    contract_labor = 0
    invoice_labor = 0
    travel_costs = 0
    travel_meals = 0
    business_property_exp = 0
    office_expenses = 0
    usd_hosts_paid = 0
    # loop through expenses dict in tax_data col in db table
    for exp_type, expense_info in expenses.items():
        # if there is a cost associated, and the cost is not an empty string/falsy
        if "cost" in expense_info and expense_info['cost']:
            exp_amt = float(expense_info['cost'])
        
            # get expenses that fall under "supplies" 
            if exp_type in SUPPLIES_EXPENSES:
                supplies_expenses += exp_amt
        
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
            else:
                logger.warning(f"Host paid in non-USD currency (id: {dbid} - {name}, {tax_year})")

    # PART 2 - now that we have all expenses organized - categorize to schc fields
    # Sum together claimable expenses for reporting, add to pdf data 
    tax_data['11'] = contract_labor
    tax_data['18'] = office_expenses
    tax_data['20b'] = business_property_exp
    tax_data['22'] = supplies_expenses
    tax_data['24a'] = travel_costs
    tax_data['24b'] = travel_meals
    tax_data['25'] = utilities_expense

    # sum these up for total 
    expenses_claim_sum = contract_labor + office_expenses + business_property_exp + supplies_expenses + travel_meals + travel_costs + utilities_expense
    tax_data['28'] = expenses_claim_sum
    logger.info(f"Sum of all claimable expenses: ${expenses_claim_sum}")

    # Subtract expense from rewards
    net_profit = income - expenses_claim_sum
    logger.info(f"Total taxable earnings for year {tax_year}: ${net_profit}")
    tax_data['31'] = net_profit

    # other expenses - add invoice labor here
    if invoice_labor:
        tax_data['part5-expense-entry'] = "Professional installation"
        tax_data['part5-expense-amt'] = invoice_labor
        tax_data['part5-other-expenses-sum'] = invoice_labor

    # Write tax_data to pdf 
    name_no_space = name.replace(" ", "_")
    output_pdf = f"{name_no_space}_{tax_year}_1040sc.pdf"
    logger.debug(f"Input dict for tax form: {tax_data}")
    local_file = write_data_to_1040(output_pdf, tax_data)

    # save to aws s3
    aws_filename = f"{dbid}/{output_pdf}"
    save_1040_to_s3(local_file, file_year=tax_year, aws_file_name=aws_filename)

    # delete local file version of sch c
    os.remove(local_file)

    
    
