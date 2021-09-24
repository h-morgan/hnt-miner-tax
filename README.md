# Helium Miner Tax Tool 

This tool is a cli tool that can be run to determine a Helium miner's rewards income in USD for a requested tax year. 

Once initial setup is complete, to run the tool you need to give it a user's Helium wallet address and the tax year of interest. Additional instructions are included below.

## Table of Contents
- [1. Setup](#1-setup)
- [2. How to run](#2-how-to-run)
  - [A. Generate Helium Rewards CSV](#a-generate-helium-rewards-csv)
    - [CLI Arguments](#cli-arguments)
    - [Input Arguments](#input-arguments)
    - [CSV Output](#csv-output)
  - [B. Compute Taxes for a Client](#b-compute-taxes-for-a-client)

## 1. Setup 

First, clone the repository onto your machine:
```bash
git clone git@github.com:h-morgan/hnt-miner-tax.git
```
Then move into the cloned repository on your local machine, and perform the following commands there.

Next, initialize a virtual environment using venv. Ensure you are using python3:
```bash
python3 -m venv venv
```

Once you have your virtual environment initalized, next step is to activate it:
```bash
source venv/bin/activate
```

Now that its activated, we need to install the required packages:
```bash
pip install -r requirements.txt
```
Note: you will only need to intialize a venv and install the required packages one time upon setup. From here on out, you will only need to ensure the venv is activated and you will be able to run the tool.

## 2. How to run
There are 2 possible ways to run the cli tool (see their respective sections for more info) - 

[a](#a-generate-helium-rewards-csv) - generate the USD sum of all Helium rewards given a Helium wallet address and a tax year, as well as a CSV output of all transactions

[b](#b-compute-taxes-for-a-client) - compute taxes for a client given an input json file

You can pass the required information as arguments to the cli tool one of two ways: via cli arguments, or input arguments.

### A. Generate Helium Rewards CSV


#### CLI Arguments

To run the tool with the wallet address and tax year as inline cli arguments, it looks like this:
```bash
python cli.py rewards-csv --account abcde12345 --year 2020
```
Where **abcde12345** is your Helium wallet address, and **2020** is the year of interest. You should update these two to be the values you need (your own wallet address and year you want to compute your taxes for).

#### Input Arguments
A second way to run the tool is via prompted input arguments. To run the tool this way, just run the following command:
```bash
python helium.py
```
You will then be prompted within the terminal for your wallet address, which you can enter directly in the terminal and then hit enter. Next, you will be prompted for the year, which you can enter as well and hit enter. After you provide those 2 pieces of information, the tool will run on its own.

#### CSV Output

This service produces a csv file detailing all of the HNT rewards earned connected to the specified wallet provided, for the tax year requested. The csv contains the following fields:

```bash
timestamp, wallet address, hotspot address, block, hnt amt, oracle price, usd, hash
```
The file will be saved in the root of the project folder locally on your machine. The service will also output a sum total of all rewards earned in the requested tax year in USD, which will be printed out directly in the terminal.

### B. Compute Taxes for a Client

This option requires an input json file to be provided in a `clients/` directory within the top level of this repo. The json file provided needs to have the following contents:

```json
{
    "first_name": "Sam",
    "last_name": "Smith",
    "email": "sam@test.com",
    "tax_year": 2020,
    "helium_wallet_address": "1234567abcdefg09876",
    "state_of_residence": "Massachusetts",
    "expenses": [
        {
            "type": "hotspot",
            "amount_usd": 400.00
        },
        {
            "type": "antenna",
            "amount_usd": 70.00
        },
        {
            "type": "hardware_equipment_other",
            "amount_usd": 10.00
        },
        {
            "type": "internet",
            "amount_usd": 350.00
        }
    ]
}
```

The expenses section of this sample is just showing possible examples of expenses, but at a minimum there needs to be an expenses key with a list of contents describing the expenses of that tax year (can be empty as well). 

FUTURE NOTE: The idea is these json files will eventually be generated from the forms users will fill out on the hnttax.us website, but for now I'm manually creating these json inputs