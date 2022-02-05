# hntTax - HNT Rewards and Schedule C Compiler

This tool is a cli tool that can be run to determine a Helium miner's rewards income in USD for a requested tax year. 

## Table of Contents
- [1. Setup](#1-setup)
  - [Initial repo setup](#initial-repo-setup)
  - [Environment variables](#environment-variables)
- [2. How to run](#2-how-to-run)
  - [Process CSV Requests](#process-csv-requests)
  - [Process Schedule C Requests](#process-schedule-c-requests)
- [3. AWS](#aws)
  - [Updating AWS ECR image](#updating-aws-ecr-image)
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

If you're running this service during development/debugging, provide the following additional env var to save outputs to a `dev` folder within S3:
```
DEV_S3_FOLDER=dev
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

To run this service and generate CSV's as well as completed Schedule C forms (in both PDF and TXF format) for all new Schedule C requests in our hnttax database (all rows in the `hnt_schedc_requests` table with `status=new`):

```
python process.py -s schc
```

To run this service for a given row id in our database `hnt_schedc_requests` table:

```
python process.py -s schc --id <id>
```

This will update the following database columns:
- **processed_at** (time of completed process)
- **status** (--> `processed`, `processed_no_rewards`, or `error`)
- **service** (1, 2, 3, or null, correspoding with the options in the `services` table)
- **errors** (updates with a json of any errors encountered during processing)
- **income** (total USD income from mining - hotspots and validators combined)
- **num_hotspots** (total number of hotspots associated with wallet)
- **hotspot_locations** (a list of json data containing location info for each hotspot)
- **flags** (a json of booleans of any flags encountered during processing - for example, `hotspot_moved_states: true`)

The process will also save output files in our AWS S3 bucket. It will create a folder (or save to an existing folder, if there were receipts uploaded during the [hnttax-form-fetch](https://github.com/h-morgan/hnttax-form-fetch) process). The process will save the following to a folder (named corresponding with the db id):
- csv of hotspot mining rewards summary (if any)
- csv of validator rewards summary (if any)
- Schedule C form PDF
- SChedule C form TXF

This will be in addition to any receipts that the client uploaded, which (if any) are retrieved during the [hnttax-form-fetch](https://github.com/h-morgan/hnttax-form-fetch) process.

## AWS

This service is meant to run in production as tasks in AWS containers. For more info on how we define and provision containers in AWS to run tasks, see this [hntTax Google doc](https://docs.google.com/document/d/1OQaZ1h---u0dqlE_gmk0jjOhQ7R5jFZjhOjNi4OLvxQ/edit#).

### Updating AWS ECR image
Any time this repo is updated/any code changes are made, in order for those changes to be reflected in the tasks run in aws, the ECR image needs to updated. 

This process can be done by running the script to build the new image, tag it, and push to AWS:

```
./prod-upload.sh
```
