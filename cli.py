import click
from click.termui import prompt
from helium import URL_ACCOUNTS_BASE, get_request, get_helium_rewards, compute_taxes
import os
import json

@click.group()
def cli():
    pass

@cli.command(name="rewards-csv")
@click.option("--account", prompt=True)
@click.option("--year", prompt=True)
def generate_rewards_csv(account, year):
    """
    Generate a CSV output of a Helium wallet's total rewards
    for a specified tax year. Saves csv
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
        usd_rewards = get_helium_rewards(account, year, save_csv=True)

    
@cli.command(name="taxes")
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