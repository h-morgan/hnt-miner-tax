from abc import abstractclassmethod, abstractstaticmethod
from loguru import logger
from db.hntdb import hnt_db_engine, hnt_metadata
from sqlalchemy import select
from abc import abstractstaticmethod


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

    def get_forms(self):
        """
        Calls _get_rows method to get rows one by one, then calls _transform_row
        method to transform each row into required payload format for hnt db
        """
        for row in self._get_rows():
            yield self._transform_row(row)