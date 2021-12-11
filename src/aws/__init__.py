import boto3
from io import StringIO
from loguru import logger
import os

# map location for each key (csv, schc) for where to save files in aws
SAVE_MAP = {
    'csv': 'csv_summary',
    'schc': 'schedc'
}


def save_df_to_s3(df, request_type='csv', file_year=2021, file_name='test.csv'):
    "save a given df to s3. type can either be csv, or schc"

    # build file path to save df to, given args
    saved_file = f"{SAVE_MAP[request_type]}/{file_year}/{file_name}"

    # if we're running in dev, prefix the file folder to save to a dev folder
    if os.getenv("DEV_S3_FOLDER"):
        saved_file = f"dev/{saved_file}"

    # bucket name in s3
    bucket = 'service-outputs'

    logger.info(f"[AWS] Saving CSV to AWS, in s3 bucket: {bucket}, path: {saved_file}")

    csv_buffer = StringIO()
    df.to_csv(csv_buffer)
    s3 = boto3.resource('s3')
    s3.Object(bucket, saved_file).put(Body=csv_buffer.getvalue())