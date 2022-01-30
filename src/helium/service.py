import os
from loguru import logger
import requests
from requests import adapters
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util import retry
from requests.packages.urllib3.util.retry import Retry
from urllib.parse import urljoin


class HeliumClient:
    """
    Client that sets up connection to Helium API
    """

    _session = None
    base_url = None
    service_name = 'HELIUM API'

    # Helium API updates as of 11/2021 require passing User-Agent param in header in requests - mocking a browser here
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'# This is another valid field
    }

    URL_ACCOUNTS_BASE = None
    URL_HOTSPOTS_BASE = None
    URL_ORACLE_BASE = None
    URL_VALIDATORS_BASE = None

    def __init__(self, base_url=None):
        self.base_url = base_url or os.getenv("HELIUM_API_URL")

        session = requests.Session()
        retry = Retry(total=25, backoff_factor=1, status_forcelist=(500, 502, 503, 504, 429))
        retry.BACKOFF_MAX = 420
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        self._session = session

        self.URL_ACCOUNTS_BASE = urljoin(self.base_url, "accounts")
        self.URL_HOTSPOTS_BASE = urljoin(self.base_url, "hotspots")
        self.URL_ORACLE_BASE = urljoin(self.base_url, "oracle/prices")
        self.URL_VALIDATORS_BASE = urljoin(self.base_url, "validators")


    def validate_wallet(self, wallet_addr):

        # build url to hit in helium with given wallet address
        url = self.URL_ACCOUNTS_BASE + f'/{wallet_addr}'

        # make request, raise exceptions if they come up
        resp = self._session.get(url, headers=self.HEADERS)
        logger.debug(f"[{self.service_name}] valid wallet check url: {url}")
        resp.raise_for_status()

        # load response body
        wallet_data = resp.json()
        logger.debug(f"[{self.service_name}] validate wallet response body: {wallet_data}")
        
        # get block value of account - this is the block the wallet was recorded on
        block = wallet_data['data']['block']

        # if block value is None, check to see if this is actually a hotspot address, 
        # if so get the associated wallet ("owner") in Helium api response
        if block is None:
            logger.warning(f"[{self.service_name}] wallet addr not found in blockchain, checking if hotspot addr")
            
            valid_wallet = self._get_valid_wallet_from_hotpost(wallet_addr)

        else:
            valid_wallet = wallet_addr

        return valid_wallet

    def _get_valid_wallet_from_hotpost(self, hotspot_address):
        # build url to hit in helium with given wallet address
        url = self.URL_HOTSPOTS_BASE + f'/{hotspot_address}'

        # make request, raise exceptions if they come up
        try:
            resp = self._session.get(url, headers=self.HEADERS)
            logger.debug(f"[{self.service_name}] validate hotspot check url: {url}")

            # load response body
            hotspot_data = resp.json()
            logger.debug(f"[{self.service_name}] validate hotspot response body: {hotspot_data}")
        
            # if we received a valid response, it will have a "data" key
            if "data" in hotspot_data:
                wallet_addr = hotspot_data['data']['owner']
                logger.info(f"[{self.service_name}] hotspot address provided - found valid wallet for hotspot ({wallet_addr})")
                return wallet_addr

            if "error" in hotspot_data:
                logger.error(f"[{self.service_name}] invalid wallet address given was not a hotspot address")
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"[{self.service_name}] invalid wallet address given was not a hotspot address ({e})")
        

    def get_hotspots_for_wallet(self, wallet_addr):
        
        # build url to hit in helium with given wallet address
        url = '/'.join([self.URL_ACCOUNTS_BASE, wallet_addr, 'hotspots'])        # make request, raise exceptions if they come up
        
        # make request, raise exceptions if they come up
        resp = self._session.get(url, headers=self.HEADERS)
        resp.raise_for_status()

        # load response body
        hotspots_data = resp.json()

        return hotspots_data


    def get_validators_for_wallet(self, wallet_addr):
        
        # build url to hit in helium with given wallet address
        url = '/'.join([self.URL_ACCOUNTS_BASE, wallet_addr, "validators"])        # make request, raise exceptions if they come up
        
        # make request, raise exceptions if they come up
        resp = self._session.get(url, headers=self.HEADERS)
        resp.raise_for_status()

        # load response body
        validators_data = resp.json()

        return validators_data


    def get_hotspot_state_locations(self, hotspots_data):
        """
        Takes in response from wallet/:addr/hotspots request and parses data
        to compile list of states where hotspots are located
        """
        all_hotspot_locations = []
        states = []
        non_usd_location = False

        if not hotspots_data['data']:
            logger.warning(f"No hotspots found for this wallet. Hotspot data: {hotspots_data}")
        
        else:
            for hotspot in hotspots_data['data']:
                hotspot_country = hotspot['geocode']['short_country']
                hotspot_state = hotspot['geocode']['short_state']
                if hotspot_country != 'US' and hotspot_country:
                    logger.warning("Non-US country detected in hotspot locations")
                    non_usd_location = True
                
                all_hotspot_locations.append({
                    "hotspot_name": hotspot['name'],
                    "hotspot_country": hotspot_country,
                    "hotspot_state": hotspot['geocode']['short_state'],
                    "hotspot_city": hotspot['geocode']['short_city']
                })

                # keep track of JUST states, to see if they're all unique
                states.append(hotspot_state)
        
        if states:
            is_single_state = all(state == states[0] for state in states)
        
        else:
            is_single_state = True
        
        return all_hotspot_locations, is_single_state, non_usd_location


    def get_hotspot_rewards(self, year, hotspot_addr):

        next_year = str(int(year) + 1)
        url_query = f"rewards?max_time={next_year}-01-01&min_time={year}-01-01" # should be 01-01
    
        next_cursor = None

        while True:
            # need this here to reset base url for this query each time we loop
            url = '/'.join([self.URL_HOTSPOTS_BASE, hotspot_addr, url_query]) 

            # if we don't have a cursor value (usually first request) hit endpoint normally
            if next_cursor is None:
                logger.info(f"[{self.service_name}] Getting initial data for Helium hotspot {hotspot_addr} for year {year}")
                resp = self._session.get(url, headers=self.HEADERS)

            else:
                url = '&'.join([url, f"cursor={next_cursor}"])
                resp = self._session.get(url, headers=self.HEADERS)

            resp.raise_for_status()
            logger.info(f"[{self.service_name}] Rewards request status: {resp.status_code}, url: {url}")
            resp_data = resp.json()

            # if there's data, yield it
            if 'data' in resp_data:
                num_rewards = len(resp_data['data'])
                logger.info(f"[{self.service_name}] {num_rewards} new rewards transactions being recorded")
                for reward in resp_data['data']:
                    yield reward

            # determine if paginated results + update cursor value if so
            if resp_data.get('cursor'):
                # find number of rewards transactions on this page - for logging
                logger.info(f"[{self.service_name}] Retrieved paginated cursor data")
                next_cursor = resp_data.get('cursor')

            # if there's no next cursor, we break
            if resp_data.get('cursor') is None:
                break

    
    def get_validator_rewards(self, year, validator_addr):

        next_year = str(int(year) + 1)
        url_query = f"rewards?max_time={next_year}-01-01&min_time={year}-01-01" # should be 01-01
    
        next_cursor = None

        while True:
            # need this here to reset base url for this query each time we loop
            url = '/'.join([self.URL_VALIDATORS_BASE, validator_addr, url_query]) 

            # if we don't have a cursor value (usually first request) hit endpoint normally
            if next_cursor is None:
                logger.info(f"[{self.service_name}] Getting initial data for Helium validator {validator_addr} for year {year}")
                resp = self._session.get(url, headers=self.HEADERS)

            else:
                url = '&'.join([url, f"cursor={next_cursor}"])
                resp = self._session.get(url, headers=self.HEADERS)

            resp.raise_for_status()
            logger.info(f"[{self.service_name}] Rewards request status: {resp.status_code}, url: {url}")
            resp_data = resp.json()

            # if there's data, yield it
            if 'data' in resp_data:
                num_rewards = len(resp_data['data'])
                logger.info(f"[{self.service_name}] {num_rewards} new rewards transactions being recorded")
                for reward in resp_data['data']:
                    yield reward

            # determine if paginated results + update cursor value if so
            if resp_data.get('cursor'):
                # find number of rewards transactions on this page - for logging
                logger.info(f"[{self.service_name}] Retrieved paginated cursor data")
                next_cursor = resp_data.get('cursor')

            # if there's no next cursor, we break
            if resp_data.get('cursor') is None:
                break

    def transform_reward(self, reward):
        """
        Take in a rewards object from helium api (from query to hotspot address endpoint with query params and cursor)
        and transform into format needed to save to csv

        Returns 1 complete csv row (exception of location data columns that are per hotspot, not per reward)
        """
        timestamp = reward['timestamp']
        hash_ = reward['hash']
        block = reward['block']
        hnt_amt = reward['amount'] * (10 ** -8)

        # get block price to convert hnt amount to usd 
        usd, oracle_price = self.convert_hnt_usd(block, hnt_amt)

        # build list of elements to return
        return {
            "timestamp": timestamp,
            "block": block,
            "hnt": hnt_amt,
            "oracle_price": oracle_price,
            "usd": usd
        }

    def convert_hnt_usd(self, this_block, hnt_amt):
        # get block price, if we can't get this block get the one before it
        block = this_block
        usd = None
        while usd is None:
            url_oracle = '/'.join([self.URL_ORACLE_BASE, str(block)])
            oracle_response = self._session.get(url_oracle, headers=self.HEADERS)
            oracle_data = oracle_response.json()
            
            # if we have data for this block, get the oracle price
            if 'data' in oracle_data:
                oracle_price = oracle_data['data']['price'] * (10 ** -8)
                usd = oracle_price * hnt_amt
                return usd, oracle_price
            
            # if we get an error, handle it accordingly
            if 'error' in oracle_data:
                logger.error(f"[{self.service_name}] Error accessing data for block {block}, response from Helium: {oracle_data}")
                block = block - 1
