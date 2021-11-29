import pymysql
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, MetaData
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