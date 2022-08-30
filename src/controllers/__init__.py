from logging import LogRecord
from sqlalchemy.sql.schema import MetaData
import stripe
import os
from loguru import logger
from pathlib import Path



def create_stripe_customer(name, email, db_id, service_level):

    # load and set stripe API key
    STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
    stripe.api_key = STRIPE_API_KEY

    # check if we already have a customer for this email addr
    customers = stripe.Customer.list(email=email)

    # if we got back a data object with a non-empty list, the customer already exists
    if customers['data']:
        logger.info(f"[stripe] Customer with email {email} already exists in stripe")    
    
    else:
        logger.info(f"[stripe] Customer added to Stripe ({name}, {email})")
        stripe.Customer.create(
            email = email,
            name = name,
            metadata = {
                "hnttax_db_id": db_id,
                "service_level": service_level
            }
        )

def save_csv(df, request_type='csv', file_year=2021, file_name='temp.csv'):
    "save a given df to csv temp file. type can either be csv, or schc"

    # get root directory
    root_dir = os.getenv("TEMP_FILE_LOCATION")

    # get file stem (NOTE: was using this when trying to zip file)
    file_stem = Path(file_name).stem

    # if we're running in dev, prefix the file folder to save zip file to a dev folder
    if os.getenv("DEV"):
        file_path = f"{root_dir}dev/{file_name}"
    else:
        file_path = f"{root_dir}{file_name}"

    # compress the file - NOTE: was using this when trying to zip file
    compression_opts = dict(method='zip', archive_name=file_name)  

    logger.info(f"Saving CSV to temp dir locally, path: {file_path}")
    df.to_csv(file_path, index=False) 


