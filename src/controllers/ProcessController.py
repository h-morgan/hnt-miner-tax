import re
import click
from processors.CsvProcessor import CsvProcessor
from db.hntdb import hnt_db_engine as hnt_db
from db.hntdb import hnt_metadata
from loguru import logger
from helium.service import HeliumClient
from sqlalchemy.dialects.postgresql import insert as pinsert
import pandas as pd
from datetime import datetime


def process_csv_requests(id_=None):
    """
    Processes all new csv requests in hnttax db (status="new")
    if id given, takes in db id to run the csv processor for
    """

    processor = CsvProcessor()
    client = HeliumClient()

    csv_table = hnt_metadata.tables[processor.HNT_DB_TABLE_NAME]

    # loop over new form entries 1 by 1, and run the csv-creation code
    for form in processor.get_forms(id_=id_):
        
        row_id = form['id']
        wallet = form['wallet']
        year = form['year']

        valid_wallet = client.validate_wallet(form['wallet'])

        # if we didn't get a valid wallet address, we log the error, write the message to the db, and continue on to next form
        if valid_wallet is None:
            logger.error(f"[{processor.HNT_SERVICE_NAME}] invalid helium wallet address for db id: {row_id}")
            error_info = {
                "msg": "wallet not found on Helium blockchain/no wallet data",
                "stage": "wallet validation"
            }
            update_values = {
                "status": "error",
                "errors": error_info,
                "processed_at": datetime.utcnow()
            }
            error_stmt = csv_table.update().where(csv_table.c.id == row_id)
            hnt_db.execute(error_stmt, update_values)
        
        # otherwise, process the csv request
        else:
            logger.info(f"[{processor.HNT_SERVICE_NAME}] valid wallet found on Helium blockchain, processing request for tax year {year}, wallet: {wallet}")

            # get all hotspots associated with this wallet
            hotspots = client.get_hotspots_for_wallet(wallet)
            logger.info(f"[{processor.HNT_SERVICE_NAME}] num hotspots associated with this address: {len(hotspots['data'])}")
            
            all_rewards = []
            # loop through each hotpost and compile list of all transactions associated with this wallet
            for hotspot in hotspots['data']:
                hotspot_addr = hotspot['address']
                hotspot_state = hotspot['geocode']['short_state']
                logger.info(f"[{processor.HNT_SERVICE_NAME}] retrieving hotspot reward activity for hotspot: {hotspot_addr}")

                # collect hotspot-level attributes that are written to csv
                hotspot_attr = {
                    "wallet": wallet,
                    "hotspot_address": hotspot_addr,
                    "state": hotspot_state
                }

                # add this hotspot's rewards data to the list of all rewards
                for reward in client.get_hotspot_rewards(year, hotspot_addr):
                    
                    # transform the returned reward data into our format for saving to csv
                    transformed_reward = client.transform_reward(reward)
                    complete_row = {
                        **transformed_reward,
                        **hotspot_attr
                    }
                    all_rewards.append(complete_row)

            # once all rewards are collected for a wallet, convert to dataframe and save to csv
            if all_rewards:
                df = pd.DataFrame(all_rewards)
            
                # TODO: save to aws s3
                logger.info(f"[{processor.HNT_SERVICE_NAME}] Compilation of all reward transactions for db id {row_id} from year {year} complete. Saving to csv.")
                df.to_csv(f"{row_id}_{year}.csv")

                # Once csv is compiled, we need the total in the USD column 
                total_usd = round(df['usd'].sum(), 3)
                logger.info(f"[{processor.HNT_SERVICE_NAME}] Total usd income for year {year}: ${total_usd}") 

                # update hnttax db for this request
                update_success_values = {
                    "status": "processed",
                    "income": total_usd,
                    "processed_at": datetime.utcnow()
                }
                update_success_stmt = csv_table.update().where(csv_table.c.id == row_id)
                hnt_db.execute(update_success_stmt, update_success_values)
            
            else:
                msg = "No reward transactions found"
                logger.warning(f"[{processor.HNT_SERVICE_NAME}] {msg} for wallet {wallet} for year {year}")
                update_empty = {
                    "status": "empty",
                    "errors": {
                        "msg": msg,
                        "stage": "all hotspot reward collection for wallet - empty csv"
                    },
                    "processed_at": datetime.utcnow()
                }
                update_empty_stmt = csv_table.update().where(csv_table.c.id == row_id)
                hnt_db.execute(update_empty_stmt, update_empty)

    logger.info(f"[{processor.HNT_SERVICE_NAME}] DONE - completed processing all new CSV requests")


def process_schc_requests(id):
    pass

