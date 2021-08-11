from click.termui import prompt
import requests
import pandas as pd
import json, time, random
import click


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
        print(f"Hit an error, trying to hit url again: {url_cursor}")
        time.sleep(2**try_number + random.random()*0.01) #exponential backoff
        return query_helium_cursor(cursor, base_trans_url, try_number=try_number+1)
    
    num_data_entries = len(cursor_data['data'])
    print(f"Retrieved cursor data, found {num_data_entries} new transactions")
    return cursor_data


def get_request(url, try_number=1):
    """
    Submits a GET request to the url specified, performs re-tries in the event of an error
    """
    try:
        res = requests.get(url)
        res_data = res.json()
    
    except Exception as e:
        print(f"Error performing request, trying to hit url again: {url}")
        print("ERROR MSG:", e)
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
        print("getting next round of data from next cursor")
        return get_transaction_data(cursor_data['cursor'], base_trans_url, wallet_addr, hotspot_addr, prev=previous_data)

    else:
        return previous_data


def main(account, year):
    """
    Hit the helium api to retreive the total rewards for all hotspots associated with an account
    """

    # Get list of hotspot addresses associated with given account
    url_accounts = '/'.join([URL_ACCOUNTS_BASE, account, 'hotspots'])
    account_data = get_request(url_accounts)

    num_hotspots = len(account_data['data'])
    print(f"Number of hotspots found associated with account = {num_hotspots}")

    # Loop through each hotspot to look at rewards associated with that hotspot address
    all_transactions = []
    for hotspot in account_data["data"]:
        print("="*100)
    
        # Get identifying info needed for this hotspot - timezone and hotspot address/id
        hs_address = hotspot['address']
        print("HOTSPOT ADDRESS:", hs_address)

        # loop through each hotspot and get transactions for it
        url_query = f"rewards?max_time={year}-12-31&min_time={year}-01-01"
        url_transactions = '/'.join([URL_HOTSPOTS_BASE, hs_address, url_query])

        transaction_data = get_request(url_transactions)
        print(transaction_data['cursor'])

        # get all data by paging through the cursors until we are done
        if 'cursor' in transaction_data:
            print("Getting initial cursor data")
            all_hs_data = get_transaction_data(transaction_data['cursor'], url_transactions, wallet_addr=account, hotspot_addr=hs_address, prev=None)

            if all_hs_data:
                all_transactions.extend(all_hs_data)

    df_columns = ['timestamp', 'account', 'hotspot_address', 'block', 'hnt', 'oracle_price', 'usd', 'hash']
    df = pd.DataFrame(all_transactions, columns=df_columns)

    print(f"Compilation of all reward transactions from year {year} complete. Saving to csv file for review.")
    df.to_csv(f"{account[-8:]}_{year}.csv")

    # Once csv is compiled, we need the total in the USD column 
    total_usd = round(df['usd'].sum(), 4)
    print(f"Total usd income for year {year}: ${total_usd}")


@click.command()
@click.option("--account", prompt=True)
@click.option("--year", prompt=True)
def helium(account, year):
    """
    Kickoff point of script, gets cli args and runs main script
    """
    # make sure year is numeric
    if not year.isnumeric() or len(year) != 4:
        print('Year must be a numeric of format YYYY')
        return

    # determine if the account requested exists in helium
    verify_account_url = URL_ACCOUNTS_BASE + '/' + account
    valid_account_data = get_request(verify_account_url)

    # Block value of account -if "null", invalid Helium acct
    block = valid_account_data['data']['block']
    if not block:
        print("Helium account address requested is invalid")
    
    else:
        print(f"Account found on Helium blockchain, processing request for tax year {year}.")
        main(account, year)


if __name__ == "__main__":

    helium()
