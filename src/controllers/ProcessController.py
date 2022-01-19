from processors.CsvProcessor import CsvProcessor
from processors.SchcProcessor import SchcProcessor
from db.hntdb import hnt_db_engine as hnt_db
from db.hntdb import hnt_metadata
from loguru import logger
from helium.service import HeliumClient
from sqlalchemy.dialects.postgresql import insert as pinsert
import pandas as pd
from aws import save_df_to_s3
from datetime import datetime
from taxes.taxes import write_schc
from taxes.utils import collect_flags


# key for determining service level for schc processing
SERVICE_KEY = {
    "single_state": 1,
    "single_state_mult_miners": 2,
    "mult_state_mult_miners": 3
}


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

        # if the valid wallet returned from validation is different from db value, update db
        if valid_wallet is not None and valid_wallet != wallet:
            logger.info(f"[{processor.HNT_SERVICE_NAME}] updating helium wallet address in db - hotspot address provided")
            update_wallet_values = {
                "wallet": valid_wallet
            }
            update_wallet_stmt = csv_table.update().where(csv_table.c.id == row_id)
            hnt_db.execute(update_wallet_stmt, update_wallet_values)
 
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
            logger.info(f"[{processor.HNT_SERVICE_NAME}] valid wallet found on Helium blockchain, processing request for tax year {year}, wallet: {valid_wallet}")

            # get all hotspots associated with this wallet
            hotspots = client.get_hotspots_for_wallet(valid_wallet)
            num_hotspots = len(hotspots['data'])
            logger.info(f"[{processor.HNT_SERVICE_NAME}] num hotspots associated with this address: {num_hotspots}")
            
            all_rewards = []
            x = 1
            # loop through each hotpost and compile list of all transactions associated with this wallet
            for hotspot in hotspots['data']:
                logger.info(f"[{processor.HNT_SERVICE_NAME}] hotspot {x} of {num_hotspots}")
                hotspot_addr = hotspot['address']
                hotspot_state = hotspot['geocode']['short_state']
                logger.info(f"[{processor.HNT_SERVICE_NAME}] retrieving hotspot reward activity for hotspot: {hotspot_addr}")

                # collect hotspot-level attributes that are written to csv
                hotspot_attr = {
                    "wallet": valid_wallet,
                    "hotspot_address": hotspot_addr
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

                # increment the hotspot counter, for logging
                x += 1

            # once all rewards are collected for a wallet, convert to dataframe and save to csv
            if all_rewards:
                df = pd.DataFrame(all_rewards)
            
                logger.info(f"[{processor.HNT_SERVICE_NAME}] Compilation of all reward transactions for db id {row_id} from year {year} complete. Saving to csv in AWS.")
                file_name = f"{row_id}_{year}_{valid_wallet[0:7]}.csv"
                save_df_to_s3(df, request_type='csv', file_year=year, file_name=file_name)

                # Once csv is compiled, we need the total in the USD column 
                total_usd = round(df['usd'].sum(), 3)
                logger.info(f"[{processor.HNT_SERVICE_NAME}] Total usd income for year {year}: ${total_usd}") 

                # update hnttax db for this request
                update_success_values = {
                    "status": "processed",
                    "income": total_usd,
                    "processed_at": datetime.utcnow(),
                    "num_hotspots": num_hotspots,
                }
                update_success_stmt = csv_table.update().where(csv_table.c.id == row_id)
                hnt_db.execute(update_success_stmt, update_success_values)
            
            else:
                msg = "No reward transactions found"
                logger.warning(f"[{processor.HNT_SERVICE_NAME}] {msg} for wallet {valid_wallet} for year {year}")
                update_empty = {
                    "status": "empty",
                    "errors": {
                        "msg": msg,
                        "stage": "all hotspot reward collection for wallet - empty csv"
                    },
                    "processed_at": datetime.utcnow(),
                    "num_hotspots": num_hotspots,
                }
                update_empty_stmt = csv_table.update().where(csv_table.c.id == row_id)
                hnt_db.execute(update_empty_stmt, update_empty)

    logger.info(f"[{processor.HNT_SERVICE_NAME}] DONE - completed processing all new CSV requests")


def process_schc_requests(id_=None):
    """
    Processes all new csv requests in hnttax db (status="new")
    if id given, takes in db id to run the csv processor for
    """

    processor = SchcProcessor()
    client = HeliumClient()

    schc_table = hnt_metadata.tables[processor.HNT_DB_TABLE_NAME]

    # loop over new form entries 1 by 1, and run the csv-creation code
    for form in processor.get_forms(id_=id_):
        
        row_id = form['id']
        wallet = form['wallet']
        year = form['year']
        tax_data = form['tax_data']

        ## STEP 1 - WALLET VALIDATION
        valid_wallet = client.validate_wallet(form['wallet'])

        # if the valid wallet returned from validation is different from db value, update db
        if valid_wallet is not None and valid_wallet != wallet:
            logger.info(f"[{processor.HNT_SERVICE_NAME}] updating helium wallet address in db - hotspot address provided")
            update_wallet_values = {
                "wallet": valid_wallet
            }
            update_wallet_stmt = schc_table.update().where(schc_table.c.id == row_id)
            hnt_db.execute(update_wallet_stmt, update_wallet_values)
 
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
            error_stmt = schc_table.update().where(schc_table.c.id == row_id)
            hnt_db.execute(error_stmt, update_values)
        
        # otherwise, process the schedc request
        else:
             # store all errors in json list, default is none - for db 
            errors = {}

            # keep track of the values to be written to the db
            income = None
            status = None
            processed_at = None
            num_hotspots = None
            hotspot_locations = None
            service_level = None

            logger.info(f"[{processor.HNT_SERVICE_NAME}] valid wallet found on Helium blockchain, processing request for tax year {year}, wallet: {valid_wallet}")

            ## STEP 2 - get all hotspots associated with this wallet
            hotspots = client.get_hotspots_for_wallet(valid_wallet)
            num_hotspots = len(hotspots['data'])
            logger.info(f"[{processor.HNT_SERVICE_NAME}] num hotspots associated with this address: {num_hotspots}")

            ## STEP 3 - hotspot location data and service level determination
            # get and store the state (location data) for each hotspot, using hotspot data retrieved in prior step
            hotspot_locations, is_single_state, non_us_location = client.get_hotspot_state_locations(hotspots)

            # now we have num hotspots and num unique states, determine service level
            # if we have 1 (or none, maybe not setup yet) hotspots, service level = 1
            if num_hotspots <= 1:
                service_level = SERVICE_KEY["single_state"]
            
            # more than 1 hotspot, but all in one state
            if num_hotspots > 1 and is_single_state:
                service_level = SERVICE_KEY["single_state_mult_miners"]

            elif num_hotspots > 1 and not is_single_state:
                service_level = SERVICE_KEY["single_state_mult_miners"]
            
            ## STEP 4 - compile csv rewards summary
            all_rewards = []
            x = 1
            # loop through each hotpost and compile list of all transactions associated with this wallet
            for hotspot in hotspots['data']:
                logger.info(f"[{processor.HNT_SERVICE_NAME}] hotspot {x} of {num_hotspots}")
                hotspot_addr = hotspot['address']
                hotspot_state = hotspot['geocode']['short_state']
                logger.info(f"[{processor.HNT_SERVICE_NAME}] retrieving hotspot reward activity for hotspot: {hotspot_addr}")

                # collect hotspot-level attributes that are written to csv
                hotspot_attr = {
                    "wallet": valid_wallet,
                    "hotspot_address": hotspot_addr
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

                # increment the hotspot counter, for logging
                x += 1

            # once all rewards are collected for a wallet, convert to dataframe and save to csv
            if all_rewards:
                df = pd.DataFrame(all_rewards)
            
                logger.info(f"[{processor.HNT_SERVICE_NAME}] Compilation of all reward transactions for db id {row_id} from year {year} complete. Saving to csv in AWS.")
                file_name = f"{row_id}/{row_id}_{year}_{valid_wallet[0:7]}_rewards.csv"
                save_df_to_s3(df, request_type='schc', file_year=year, file_name=file_name)

                # Once csv is compiled, we need the total in the USD column 
                total_usd = round(df['usd'].sum(), 3)
                logger.info(f"[{processor.HNT_SERVICE_NAME}] Total usd income for year {year}: ${total_usd}") 

                # update hnttax db values for this request
                income = total_usd
                num_hotspots = num_hotspots
                status = "processed"

            # if they had no mining rewards, log status as empty but still might have expenses, so still make schedc file
            else:
                msg = "No reward transactions found"
                logger.warning(f"[{processor.HNT_SERVICE_NAME}] {msg} for wallet {valid_wallet} for year {year}")
                status = "processed_no_rewards"
                errors["no_rewards"] = {
                    "msg": msg,
                    "stage": "all hotspot reward collection for wallet - empty csv"
                }
            
            ## STEP 5 - collect flags from tax form 
            flags = collect_flags(tax_data)
            if non_us_location:
                flags["non_us_hotspot"] = True
            
            ## STEP 6 - create PDF schedule c form 
            # either way, we want to create a schedule c form for this person, they may have expenses
            write_schc(income, tax_data, dbid=row_id)

            ## STEP 7 - move receipts from hnttax server to aws s3

            ## STEP 8 - update values in the database
            processed_at = datetime.utcnow()
            update_vals = {
                "status": status,
                "errors": errors,
                "income": income,
                "processed_at": processed_at,
                "num_hotspots": num_hotspots,
                "hotspot_locations": hotspot_locations,
                "service": service_level,
                "flags": flags
            }
            update_stmt = schc_table.update().where(schc_table.c.id == row_id)
            hnt_db.execute(update_stmt, update_vals)

    logger.info(f"[{processor.HNT_SERVICE_NAME}] DONE - completed processing all new schedule c requests")

