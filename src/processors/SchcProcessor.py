from sys import pycache_prefix
from processors.BaseProcessor import BaseProcessor
import json


class SchcProcessor(BaseProcessor):

    WP_FORM_ID = 85

    HNT_SERVICE_NAME = 'schc'
    HNT_DB_TABLE_NAME = 'hnt_schedc_requests'

    @staticmethod
    def _transform_row(row):

        row_id = row.id
        wallet = row.wallet
        year = row.year
        tax_data = row.tax_data
        income = row.income
        email = row.email.lower()

        # get name from tax data (used in customer creation in stripe) and capitalize
        name = tax_data['name']
        name_upper = " ".join(w.capitalize() for w in name.split())

        return {
            "id": row_id,
            "wallet": wallet,
            "year": year,
            "email": email,
            "name": name_upper,
            "tax_data": tax_data,
            "income": income
        }