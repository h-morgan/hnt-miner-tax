import requests
import pandas as pd
import json, time, random
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

URL_ACCOUNTS_BASE = "https://api.helium.io/v1/accounts"
URL_HOTSPOTS_BASE = "https://api.helium.io/v1/hotspots"
URL_ORACLE_BASE = "https://api.helium.io/v1/oracle/prices"


def query_helium_cursor(cursor, base_trans_url, try_number=1):
    """
    This function is specifically for submitting GET requests to Helium endpoints that return  `cursor` keys containing
    pointers to additional pages containing data 
    """
    
    url_cursor = '&'.join([base_trans_url, f"cursor={cursor}"])
    
    try:
        cursor_response = requests.get(url_cursor)
        cursor_data = cursor_response.json()
    
    except:
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
    try:
        res = requests.get(url)
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
        block = reward['block']
        hnt_amt = reward['amount'] * (10 ** -8)

        # get block price 
        url_oracle = '/'.join([URL_ORACLE_BASE, str(block)])
        oracle_response = requests.get(url_oracle)
        oracle_data = oracle_response.json()

        oracle_price = oracle_data['data']['price'] * (10 ** -8)
        usd = oracle_price * hnt_amt

        # build list of elements to add to our final all_transactions list (later to be used to build our df)
        reward_record = [timestamp, wallet_addr, hotspot_addr, block, hnt_amt, oracle_price, usd, hash]
        previous_data.append(reward_record)

    # Call the function again with new cursor value
    if 'cursor' in cursor_data:
        logger.debug("Getting next round of data from next cursor")
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
        logger.info("HOTSPOT ADDRESS:", hs_address)

        # loop through each hotspot and get transactions for it
        url_query = f"rewards?max_time={year}-12-31&min_time={year}-01-01"
        url_transactions = '/'.join([URL_HOTSPOTS_BASE, hs_address, url_query])

        transaction_data = get_request(url_transactions)
        logger.debug("Cursor:", transaction_data['cursor'])

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


def compute_taxes(input_json):
    """
    Takes in input data in json format, calls get_helium_rewards to determine rewards amount,
    sums up expenses, subtracts expenses from total amount
    """

    # First get the tax year and helium wallet address to get rewards
    tax_year = input_json['tax_year']
    wallet_address = input_json['helium_wallet_address']
    rewards_usd = get_helium_rewards(wallet_address, tax_year)

    # Sum up all expenses
    expenses_list = input_json['expenses']

    expenses_usd_sum = 0
    for expense in expenses_list:
        exp_type = expense['type']
        exp_amt = expense['amount_usd']
        expenses_usd_sum += exp_amt
        logger.debug(f"Expense: {exp_type} --> Amount: ${exp_amt}")

    logger.info(f"Sum of all expenses: ${expenses_usd_sum}")

    # Subtract expense from rewards
    taxable_earnings = rewards_usd - expenses_usd_sum
    logger.info(f"Total taxable earnings for year {tax_year}: ${taxable_earnings}")
    
