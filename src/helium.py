import requests
import pandas as pd
import json, time, random
import logging

from requests.api import head
from utils import fill_pdf

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

URL_ACCOUNTS_BASE = "https://api.helium.io/v1/accounts"
URL_HOTSPOTS_BASE = "https://api.helium.io/v1/hotspots"
URL_ORACLE_BASE = "https://api.helium.io/v1/oracle/prices"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'# This is another valid field
}


def query_helium_cursor(cursor, base_trans_url, try_number=1):
    """
    This function is specifically for submitting GET requests to Helium endpoints that return  `cursor` keys containing
    pointers to additional pages containing data 
    """
    
    url_cursor = '&'.join([base_trans_url, f"cursor={cursor}"])
    
    try:
        cursor_response = requests.get(url_cursor, headers=HEADERS)
        status_code = cursor_response.status_code
        cursor_data = cursor_response.json()
    
    except Exception as e:
        logger.warn(f"Hit an error, trying to hit url again: {url_cursor}")
        time.sleep(2**try_number + random.random()*0.01) #exponential backoff
        return query_helium_cursor(cursor, base_trans_url, try_number=try_number+1)

    num_data_entries = len(cursor_data['data'])
    logger.info(f"Retrieved cursor data, found {num_data_entries} new transactions")
    return cursor_data


def get_request(url, try_number=1):
    """
    Submits a GET request to the url specified, performs re-tries in the event of an error
    """
    #try:
    headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'# This is another valid field
    }   

    headers2 = {
        "User-Agent": "im dumb"
    }
    try:
        logger.info(f"URL: {url}")
        res = requests.get(url, headers=headers)
        res.status_code
        #print(res.status_code, res.text)
        res_data = res.json()

    except Exception as e:
        logger.error(f"Error performing request, trying to hit url again: {url}")
        logger.error(f"Exception hit: {e}")
        time.sleep(2**try_number + random.random()*0.01) #exponential backoff
        return get_request(url, try_number=try_number+1)

    return res_data


def get_transaction_data(cursor, base_trans_url, wallet_addr, hotspot_addr, prev=None):
    """
    Recursive function to run through transaction data paging through each cursor if present
    """
    if prev is None:
        previous_data = []
    else:
        previous_data = prev

    cursor_data = query_helium_cursor(cursor, base_trans_url)

    # Once we've got the underlying data - go through each reward transaction and add it to list
    for reward in cursor_data['data']:
        timestamp = reward['timestamp']
        hash = reward['hash']
        this_block = reward['block']
        hnt_amt = reward['amount'] * (10 ** -8)

        # get block price, if we can't get this block get the one before it
        block = this_block
        usd = None
        while usd is None:
            url_oracle = '/'.join([URL_ORACLE_BASE, str(block)])
            oracle_response = requests.get(url_oracle, headers=HEADERS)
            oracle_data = oracle_response.json()
            
            # if we have data for this block, get the oracle price
            if 'data' in oracle_data:
                oracle_price = oracle_data['data']['price'] * (10 ** -8)
                usd = oracle_price * hnt_amt
            
            # if we get an error, handle it accordingly
            if 'error' in oracle_data:
                logger.error(f"Error access data for block {block}, response from Helium: {oracle_data}")
                block = block - 1

        # build list of elements to add to our final all_transactions list (later to be used to build our df)
        reward_record = [timestamp, wallet_addr, hotspot_addr, block, hnt_amt, oracle_price, usd, hash]
        previous_data.append(reward_record)

    # Call the function again with new cursor value
    if 'cursor' in cursor_data:
        logger.info("Getting next round of data from next cursor")
        return get_transaction_data(cursor_data['cursor'], base_trans_url, wallet_addr, hotspot_addr, prev=previous_data)

    else:
        return previous_data


def get_helium_rewards(account, year, save_csv=False):
    """
    Hit the helium api to retreive the total rewards for all hotspots associated with an account
    """

    # Get list of hotspot addresses associated with given account
    url_accounts = '/'.join([URL_ACCOUNTS_BASE, account, 'hotspots'])
    account_data = get_request(url_accounts)

    num_hotspots = len(account_data['data'])
    logger.info(f"Number of hotspots found associated with account = {num_hotspots}")

    # Loop through each hotspot to look at rewards associated with that hotspot address
    all_transactions = []
    for hotspot in account_data["data"]:
        print("="*100)
    
        # Get identifying info needed for this hotspot - timezone and hotspot address/id
        hs_address = hotspot['address']
        logger.info(f"HOTSPOT ADDRESS: {hs_address}")

        # loop through each hotspot and get transactions for it
        url_query = f"rewards?max_time={year}-12-31&min_time={year}-01-01"
        url_transactions = '/'.join([URL_HOTSPOTS_BASE, hs_address, url_query])
        transaction_data = get_request(url_transactions)
        logger.info(f"Cursor: {transaction_data['cursor']}")

        # get all data by paging through the cursors until we are done
        if 'cursor' in transaction_data:
            logger.info("Getting initial cursor data")
            all_hs_data = get_transaction_data(transaction_data['cursor'], url_transactions, wallet_addr=account, hotspot_addr=hs_address, prev=None)

            if all_hs_data:
                all_transactions.extend(all_hs_data)

    df_columns = ['timestamp', 'account', 'hotspot_address', 'block', 'hnt', 'oracle_price', 'usd', 'hash']
    df = pd.DataFrame(all_transactions, columns=df_columns)

    if save_csv:
        logger.info(f"Compilation of all reward transactions from year {year} complete. Saving to csv file for review.")
        df.to_csv(f"{account[-8:]}_{year}.csv")

    # Once csv is compiled, we need the total in the USD column 
    total_usd = round(df['usd'].sum(), 4)
    logger.info(f"Total usd income for year {year}: ${total_usd}")
    return total_usd


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


def compute_taxes(input_json):
    """
    Takes in input data in json format, calls get_helium_rewards and performs steps to fill pdf
    """
    firstname = input_json['first_name']
    lastname = input_json['last_name']
    tax_year = input_json['tax_year']
    wallet_address = input_json['helium_wallet_address']
    address_line1 = input_json['address']['street']
    address_line2 = input_json['address']['city'] + ' ' + input_json['address']['state']

    logger.info(f"Preparing {tax_year} HNT taxes for: {firstname} {lastname}")
    logger.info(f"HNT wallet address: {wallet_address}")

    # build input pdf data as we go
    tax_data = {
        "name of proprietor": f"{firstname} {lastname}",
        "E1": address_line1,
        "E2": address_line2
    }

    # use tax year and helium wallet address to get rewards
    rewards_usd = get_helium_rewards(wallet_address, tax_year)
    #rewards_usd = 2400.00
    tax_data['1-line'] = rewards_usd
    tax_data['7'] = rewards_usd

    # Sum up all expenses
    expenses_list = input_json['expenses']

    expenses_usd_sum = 0
    supplies_expenses = 0
    utilities_expense = 0
    for expense in expenses_list:
        exp_type = expense['type']
        exp_amt = expense['amount_usd']
        
        # get expenses that fall under "supplies" 
        if exp_type in ['hotspot', 'hardware_equipment_other', 'antenna']:
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
    net_profit = rewards_usd - expenses_claim_sum
    logger.info(f"Total taxable earnings for year {tax_year}: ${net_profit}")
    tax_data['31'] = net_profit

    # Write tax_data to pdf 
    output_pdf = f"{firstname}_{lastname}_{tax_year}_1040sc.pdf"
    logger.debug(f"Input dict for tax form: {tax_data}")
    write_data_to_1040(output_pdf, tax_data)
    
    
