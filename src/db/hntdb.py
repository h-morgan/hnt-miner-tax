import pymysql
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, MetaData, select
import logging


# load env vars
load_dotenv()
HNT_DB_HOST = os.getenv("HNTTAX_DATABASE_HOST")
HNT_DB_UN = os.getenv("HNTTAX_DATABASE_UN")
HNT_DB_PW = os.getenv("HNTTAX_DATABASE_PW")
HNT_DB_NAME = os.getenv("HNTTAX_DATABASE_NAME")
HNT_DB_PORT = os.getenv("HNTTAX_DATABASE_PORT")


hnt_db_engine = create_engine(f'postgresql://{HNT_DB_UN}:{HNT_DB_PW}@{HNT_DB_HOST}:{HNT_DB_PORT}/hnttax')

# load metadata, to load table objects from hnt tax db
hnt_metadata = MetaData(bind=hnt_db_engine)
hnt_metadata.reflect()


def get_new_csv_requests():

    csv_table = hnt_metadata.tables['hnt_csv_requests']
    stmt = select([csv_table.c.id, csv_table.c.wallet, csv_table.c.year]).where(csv_table.c.status == 'new')

    # try to get new csv requests from db table
    try:
        new_requests = hnt_db_engine.execute(stmt)
        new_records = new_requests.fetchall()

    # if we get this error, it means we couldn't connect to hnttax database
    except (psycopg2.OperationalError, sa.exc.OperationalError):
        logger.error("Could not connect to HNTTAX database - TERMINATING")
        sys.exit()

    return new_records