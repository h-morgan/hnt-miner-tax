# hntTax - HNT Rewards and Schedule C Compiler

This tool is a cli tool that can be run to determine a Helium miner's rewards income in USD for a requested tax year. 

## Table of Contents
- [1. Setup](#1-setup)
  - [Initial repo setup](#initial-repo-setup)
  - [Environment variables](#environment-variables)
- [2. How to run](#2-how-to-run)
  - [Process CSV Requests](#process-csv-requests)
  - [Process Schedule C Requests](#process-schedule-c-requests)
- [OLD SECTIONS](#old-sections-keeping-for-now-in-case-needed)

## 1. Setup 

### Initial repo setup

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

### Environment variables

Next you'll need to create an `.env` file in the root of this repository, with the following enviroment variables:

```
HNTTAX_DATABASE_HOST=host
HNTTAX_DATABASE_PORT=5432
HNTTAX_DATABASE_UN=user
HNTTAX_DATABASE_PW=password
HNTTAX_DATABASE_NAME=hnttax

HELIUM_API_URL=https://api.helium.io/v1/
```

## 2. How to run

To run this service, navigate to the `src/` directory. From here, you can use the service's cli tool with varying commands as needed. 

Note: make sure you are running this from the activated virtual environment described above, with all required packages installed.

### Process CSV Requests

To run this service and generate CSV's for all new CSV requests in our hnttax database (all rows in the `hnt_csv_requests` table with `status=new`):

```
python process.py -s csv
```

To run this service for a given row id in our database `hnt_csv_requests` table:

```
python process.py -s csv --id <id>
```

This will update the database columns (`processed_at`, `status`, `income`, and `errors`) and will save a CSV output for each request (where a valid CSV could be generated) into our AWS S3 bucket.

### Process Schedule C Requests

This process is still in development.

<hr>

## OLD SECTIONS (KEEPING FOR NOW IN CASE NEEDED)

There are 2 possible ways to run the cli tool (see their respective sections for more info) - 

[a](#a-generate-helium-rewards-csv) - generate the USD sum of all Helium rewards for given wallet address(es) and tax year, as well as a CSV output of all transactions

[b](#b-compute-taxes-for-a-client) - generate a Schedule C form for a client given a json file


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