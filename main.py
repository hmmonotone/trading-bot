import json
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import pytz
import csv
import os

from smart_api_client import SmartApiClient

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("app.log"),
                              logging.StreamHandler()])
logger = logging.getLogger(__name__)

app = Flask(__name__)

client = SmartApiClient()
client.fetch_token_details()
active_trades = {"CE": "", "PE": ""}


def place_order(strike_price, ticker, expiry, order_type, option_type):
    client.generate_session()
    ticker = ticker
    strike_price = strike_price
    expiry = expiry
    option_type = option_type
    tradingsymbol = ticker + expiry + str(strike_price) + option_type
    if order_type == "SELL":
        tradingsymbol = active_trades[option_type]
        if tradingsymbol == "":
            logger.error("Something went wrong please check")
            return
    token_detail = client.token_json_data.get(tradingsymbol)

    if token_detail:
        order_id = client.place_order(order_type=order_type, symboltoken=token_detail.get('token'),
                                      tradingsymbol=tradingsymbol,
                                      lotsize=token_detail.get('lotsize'), exchange=token_detail.get("exch_seg"))
        if order_id and order_type == "BUY":
            active_trades[option_type] = tradingsymbol
    client.logout()


def convert_utc_to_ist(utc_time_str):
    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    ist_time = utc_time.astimezone(pytz.timezone('Asia/Kolkata'))
    return ist_time.strftime("%Y-%m-%d %H:%M:%S")


@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info(f"Received request: {request.data}")

    # Handle incoming JSON string
    try:
        json_string = request.data.decode('utf-8')
        # Fix the JSON string
        json_string = json_string.replace("'", '"')  # Replace single quotes with double quotes
        json_string = json_string.replace(';', ',')  # Replace semicolons with commas
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        return jsonify({'error': 'Invalid JSON'}), 400

    logger.info(f"Received data: {data}")

    # Extract data from webhook
    ticker = data.get('ticker')
    timenow_utc = data.get('timenow')
    timenow_ist = convert_utc_to_ist(timenow_utc)
    actual_price = float(data.get('strategy.order.price'))
    action = data.get('strategy.order.action')
    comment = data.get('strategy.order.comment')

    if comment == 'BuyCE':
        strike_price = int(int(actual_price / 100) * 100)
        place_order(strike_price=strike_price, ticker=ticker, expiry="24614", order_type="BUY", option_type="CE")
    elif comment == 'BuyPE':
        strike_price = int((int(actual_price / 100) + 1) * 100)
        place_order(strike_price=strike_price, ticker=ticker, expiry="24614", order_type="BUY", option_type="PE")
    elif "BuyPE" in comment:
        place_order(strike_price=0, ticker=ticker, expiry="24614", order_type="SELL", option_type="PE")
    else:
        place_order(strike_price=0, ticker=ticker, expiry="24614", order_type="SELL", option_type="CE")

    return jsonify({'status': 'success'}), 200


if __name__ == '__main__':
    app.run(port=5000)
