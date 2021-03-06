from controllers.ProcessController import process_csv_requests, process_schc_requests, process_test
import click
from loguru import logger
import sys


@click.command()
@click.option("--service", '-s', default='csv', type=click.Choice(["csv", "schc", "all", "test"]))
@click.option("--id", default=None)
@click.option("--log_level", '-l',  default="INFO", type=click.Choice(("INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"), case_sensitive=False))
def run(service, id, log_level):
    logger.remove()
    logger.add(sys.stderr, level=log_level.upper())
    if id: 
        logger.info(f'running for id: {id}')

    if service == "all":
        process_csv_requests(id_=id)
        process_schc_requests(id_=id)
    
    elif service == "csv":
        process_csv_requests(id_=id)

    elif service == "schc":
        print('here')
        process_schc_requests(id_=id)

    elif service == "test":
        logger.info("Running in test mode")
        process_test(id_=id)
        
    else:
        logger.warn("Incompatible service requested. Please fetch csv, schc, or both.")


if __name__ == "__main__":
    run()