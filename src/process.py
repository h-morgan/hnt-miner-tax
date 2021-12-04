from controllers.ProcessController import process_csv_requests, process_schc_requests
import click
from loguru import logger


@click.command()
@click.option("--service", '-s', default='csv', type=click.Choice(["csv", "schc", "all", "test"]))
@click.option("--id", default=None)
def run(service, id):

    if service == "all":
        process_csv_requests(id=id)
        process_schc_requests(id=id)
    
    elif service == "csv":
        process_csv_requests(id=id)

    elif service == "schc":
        process_schc_requests(id=id)

    elif service == "test":
        logger.info("Running in test mode")
        process_csv_requests(id=id)
    
    else:
        logger.warn("Incompatible service requested. Please fetch csv, schc, or both.")


if __name__ == "__main__":
    run()