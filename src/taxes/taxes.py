import json, time, random
from loguru import logger

from requests.api import head
from taxes.utils import fill_pdf
from aws import save_1040_to_s3


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

    expenses_usd_sum = 0
    supplies_expenses = 0
    utilities_expense = 0
    for exp_type, expense_info in expenses.items():
        # if there is a cost associated, and the cost is not an empty string/falsy
        if "cost" in expense_info and expense_info['cost']:
            exp_amt = float(expense_info['cost'])
        
            # get expenses that fall under "supplies" 
            if exp_type in ['hotspot', 'outdoor_bundle_kits', 'antenna']:
                supplies_expenses += exp_amt
        
            # get expenses that fall under "utilities"
            if exp_type in ['internet']:
                utilities_expense += exp_amt
            
            expenses_usd_sum += exp_amt
            logger.debug(f"Expense: {exp_type} --> Amount: ${exp_amt}")

    # Sum together claimable expenses for reporting, add to pdf data 
    expenses_claim_sum = supplies_expenses + utilities_expense
    tax_data['22'] = supplies_expenses
    tax_data['25'] = utilities_expense
    tax_data['28'] = expenses_claim_sum
    logger.info(f"Sum of all claimable expenses: ${expenses_claim_sum}")

    # Subtract expense from rewards
    net_profit = income - expenses_claim_sum
    logger.info(f"Total taxable earnings for year {tax_year}: ${net_profit}")
    tax_data['31'] = net_profit

    # Write tax_data to pdf 
    name_no_space = name.replace(" ", "_")
    output_pdf = f"{name_no_space}_{tax_year}_1040sc.pdf"
    logger.debug(f"Input dict for tax form: {tax_data}")
    local_file = write_data_to_1040(output_pdf, tax_data)

    # save to aws s3
    aws_filename = f"{dbid}/{output_pdf}"
    save_1040_to_s3(local_file, file_year=tax_year, aws_file_name=aws_filename)

    
    
