from sys import pycache_prefix
from processors.BaseProcessor import BaseProcessor
import json


class CsvProcessor(BaseProcessor):

    WP_FORM_ID = 152

    HNT_SERVICE_NAME = 'csv'
    HNT_DB_TABLE_NAME = 'hnt_csv_requests'

    @staticmethod
    def _transform_row(row):

        row_id = row.id
        wallet = row.wallet
        year = row.year

        return {
            "id": row_id,
            "wallet": wallet,
            "year": year
        }