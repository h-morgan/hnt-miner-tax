import click
from click.termui import prompt
from taxes.taxes import URL_ACCOUNTS_BASE, get_request, get_helium_rewards, compute_taxes
import os
import json
from db.hntdb import get_new_csv_requests

@click.group()
def cli():
    pass

@cli.command(name="csv-db")
def process_csv_requests():
    """
    Cli entrypoint for processing csv requests from database
    """
    # get new csv requests from database
    new_requests = get_new_csv_requests()
    print(new_requests)

    # process each request
    for req in new_requests:
        # requests are returned from db as lists of tuples of format
        # (id, wallet_address, year)
        db_id = req[0]
        wallet = req[1]
        year = req[2]

        processed = generate_rewards_csv(wallet, year)
        print(processed)

        status = processed['status']

        # if we get an error msg, update db with status "error" for this id
        if status == 'error':
            print('update db with errors')

        # if we process sucessfully, update status to "processed"
        if status == 'success':
            print('update db with success message')


@cli.command(name="csv-manual")
@click.option("--account")
@click.option("--year")
def process_one_csv(account, year):
    # make sure year is numeric
    if not year.isnumeric() or len(year) != 4:
        print('Year must be a numeric of format YYYY')
        return

    # call function to generate csv
    processed = generate_rewards_csv(account=account, year=year)
    print(processed)


def generate_rewards_csv(account, year):
    """
    Generate a CSV output of a single Helium wallet's total rewards
    for a specified tax year. Saves csv
    """

    # determine if the account requested exists in helium
    verify_account_url = URL_ACCOUNTS_BASE + '/' + account
    valid_account_data = get_request(verify_account_url)

    # Block value of account -if "null", invalid Helium acct
    block = valid_account_data['data']['block']
    if not block:
        error_msg = "Helium account address requested is invalid"
        return {
            "status": "error",
            "message": error_msg
        }
    
    else:
        print(f"Account found on Helium blockchain, processing request for tax year {year}.")
        usd_rewards = get_helium_rewards(account, year, save_csv=True)
        return {
            "rewards_total": usd_rewards,
            "status": "success",
            "wallet": account,
            "year": year
        }

    
@cli.command(name="schc")
@click.option("--filename", prompt=True)
def taxes_from_json_file(filename):
    """
    Compute the taxes for a person identified in a json file
    provided in the clients/ folder within this directory
    file: str of a filename of json file in folder containing a client's tax info 
    """
    # Check if the file is a json file
    if '.json' not in filename:
        print("Input file must be a JSON file")

    else:
        # Open the file that the user passed as an arg
        cwd = os.getcwd()
        file_path = f"{cwd}/clients/{filename}"
        json_data = json.load(open(file_path))

        # Call the compute_taxes function
        compute_taxes(json_data)
        

if __name__ == "__main__":

    cli()