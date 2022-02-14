from logging import LogRecord
from sqlalchemy.sql.schema import MetaData
import stripe
import os
from loguru import logger



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

