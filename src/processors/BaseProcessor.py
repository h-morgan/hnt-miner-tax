from abc import abstractclassmethod, abstractstaticmethod
from loguru import logger
from db.hntdb import hnt_db_engine, hnt_metadata
from sqlalchemy import select
from abc import abstractstaticmethod
import pandas as pd


class BaseProcessor:
    """
    Abstract class used ase base class for csv and schc processing
    """

    HNT_SERVICE_NAME = None
    HNT_DB_TABLE_NAME = None
    STATUSES = ["new"]

    batch_size = None

    def __init__(self, batch_size=100):
        self.batch_size = batch_size

    def _prep_select_stmt(self, max_id):
        """
        Prepares select statement used to query the hnttax db for
        new form entries in batches
        """
        hnt_table = hnt_metadata.tables[self.HNT_DB_TABLE_NAME]

        # prepare base select statement, in batches, ordered by id
        select_stmt = select([hnt_table]).where(hnt_table.c.status == 'new').limit(self.batch_size)
        select_stmt = select_stmt.order_by(hnt_table.c.id)

        # if given a max id, filter select stmt to only include ids > max_id
        if max_id is not None:
            select_stmt = select_stmt.where(hnt_table.c.id > max_id)

        return select_stmt

    def get_row_by_id(self, id_):
        hnt_table = hnt_metadata.tables[self.HNT_DB_TABLE_NAME]
        select_stmt = select([hnt_table]).where(hnt_table.c.id == id_)
        logger.debug(f"[{self.HNT_SERVICE_NAME}] fetching ID: {id_}, {select_stmt}")

        row = hnt_db_engine.execute(select_stmt).fetchone()
        return row

    def _get_rows_batch(self):
        """
        Query the hnttax db in batches of self.batch_size, yield whole batch,
        determine max id of the batch, continue process
        """
        
        logger.info(f"[{self.HNT_SERVICE_NAME}] getting batches of {self.batch_size} from hnttax table: {self.HNT_DB_TABLE_NAME}")
        max_id = None
        while True:
            select_stmt = self._prep_select_stmt(max_id)
            rows = hnt_db_engine.execute(select_stmt).fetchall()

            if not rows:
                logger.info(f"[{self.HNT_SERVICE_NAME}] end of retrieval of data rows from hnttax db")
                break

            logger.info(f"[{self.HNT_SERVICE_NAME}] retrieved {len(rows)} rows of data from hnttax db")
            yield rows

            # get max entry_id value given last set of rows
            ids = []
            for row in rows:
                ids.append(row.id)

            max_id = max(ids)

    def _get_rows(self):
        """
        Calls _get_rows_batch and yields rows one by one
        """
        for rows in self._get_rows_batch():
            for row in rows:
                yield row
        
    @abstractstaticmethod
    def _transform_row(row):
        """
        Transform one wordpress db row into format needed for HNT tax db
        """
        pass

    def get_forms(self, id_):
        """
        Calls _get_rows method to get rows one by one, then calls _transform_row
        method to transform each row into required payload format for hnt db
        """
        # if given an id, bypass the normal _get_rows method and just get our single row
        if id_:
            row = self.get_row_by_id(id_)
            yield self._transform_row(row)
        
        # otherwise run in normal mode
        else:
            for row in self._get_rows():
                yield self._transform_row(row)

    def compile_hotspot_rewards(self, helium_client, wallet, hotspots, year):
        """
        Compiles a df of hotspot rewards using the Helium client and given
        a list of hotspots
        """

        num_hotspots = len(hotspots['data'])
        all_rewards = []
        x = 1
        # loop through each hotpost and compile list of all transactions associated with this wallet
        for hotspot in hotspots['data']:
            logger.info(f"[{self.HNT_SERVICE_NAME}] hotspot {x} of {num_hotspots}")
            hotspot_addr = hotspot['address']
            logger.info(f"[{self.HNT_SERVICE_NAME}] retrieving hotspot reward activity for hotspot: {hotspot_addr}")

            # collect hotspot-level attributes that are written to csv
            hotspot_attr = {
                "wallet": wallet,
                "hotspot_address": hotspot_addr
            }

            # add this hotspot's rewards data to the list of all rewards
            for reward in helium_client.get_hotspot_rewards(year, hotspot_addr):
                
                # transform the returned reward data into our format for saving to csv
                transformed_reward = helium_client.transform_reward(reward)
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
            return df
        
        else:
            return

    def compile_validator_rewards(self, helium_client, wallet, validators, year):
        """
        Compiles a df of validator rewards using the Helium client and given
        a list of validators
        """

        num_validators = len(validators['data'])
        all_rewards = []
        x = 1
        # loop through each hotpost and compile list of all transactions associated with this wallet
        for validator in validators['data']:
            logger.info(f"[{self.HNT_SERVICE_NAME}] validator {x} of {num_validators}")
            validator_addr = validator['address']
            logger.info(f"[{self.HNT_SERVICE_NAME}] retrieving validator reward activity for validator: {validator_addr}")

            # collect hotspot-level attributes that are written to csv
            validator_attr = {
                "wallet": wallet,
                "validator_address": validator_addr
            }

            # add this hotspot's rewards data to the list of all rewards
            for reward in helium_client.get_validator_rewards(year, validator_addr):
                
                # transform the returned reward data into our format for saving to csv
                transformed_reward = helium_client.transform_reward(reward)
                complete_row = {
                    **transformed_reward,
                    **validator_attr
                }
                all_rewards.append(complete_row)

            # increment the hotspot counter, for logging
            x += 1

        # once all rewards are collected for a wallet, convert to dataframe and save to csv
        if all_rewards:
            df = pd.DataFrame(all_rewards)
            return df
        
        else:
            return
