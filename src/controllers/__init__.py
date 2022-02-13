import stripe
import os



def create_stripe_customer(name, email):


    STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")

    stripe.api_key = STRIPE_API_KEY

    stripe.Customer.create(
        email = email,
        name = name
    )