import os
from SmartApi import SmartConnect
import pyotp
import requests
from logzero import logger


class SmartApiClient:
    def __init__(self):
        self.api_key = os.getenv('API_KEY')
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')
        self.totp_token = os.getenv('TOTP_TOKEN')
        self.client_id = os.getenv('CLIENT_ID')

        if not all([self.api_key, self.username, self.password, self.totp_token, self.client_id]):
            raise ValueError("Environment variables not set properly.")

        self.smartApi = SmartConnect(self.api_key)
        self.authToken = None
        self.refreshToken = None
        self.feedToken = None
        self.token_json_data = {}

    def generate_totp(self):
        try:
            return pyotp.TOTP(self.totp_token).now()
        except Exception as e:
            logger.error("Invalid Token: The provided token is not valid.")
            raise e

    def generate_session(self):
        try:
            totp = self.generate_totp()
            data = self.smartApi.generateSession(self.username, self.password, totp)
            if not data['status']:
                logger.error(data)
                raise Exception("Session generation failed")
            self.authToken = data['data']['jwtToken']
            self.refreshToken = data['data']['refreshToken']
            self.feedToken = self.smartApi.getfeedToken()
            return data
        except Exception as e:
            logger.exception("Session generation failed: {}".format(e))
            raise e

    def fetch_token_details(self):
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # Fill token_json_data dictionary with relevant information
            self.token_json_data = {item['symbol']: item for item in data}
        except Exception as e:
            logger.exception(f"Fetching token data failed: {e}")
            return None

    def place_order(self, order_type, tradingsymbol, symboltoken, lotsize, exchange):
        try:
            orderparams = {
                "variety": "NORMAL",
                "tradingsymbol": tradingsymbol,
                "symboltoken": symboltoken,
                "transactiontype": order_type,
                "instrumenttype": "OPTIDX",
                "exchange": exchange,
                "ordertype": "MARKET",
                "price": 0,
                "producttype": "CARRYFORWARD",
                "duration": "DAY",
                "quantity": lotsize,
            }
            logger.info(f"orderparams: {orderparams}")
            orderId = self.smartApi.placeOrder(orderparams)
            logger.info(f"OrderId: {orderId}")
            return orderId
        except Exception as e:
            logger.exception(f"Order placement failed: {e}")
            return None

    def logout(self):
        try:
            logout = self.smartApi.terminateSession(self.client_id)
            logger.info("Logout Successful")
        except Exception as e:
            logger.exception(f"Logout failed: {e}")
