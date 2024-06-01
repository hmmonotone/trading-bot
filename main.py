import json
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import pytz
import csv
import os

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("app.log"),
                              logging.StreamHandler()])
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Replace with your Angel One API credentials
API_KEY = 'your_angel_one_api_key'
CLIENT_CODE = 'your_client_code'
AUTH_TOKEN = 'your_auth_token'

CSV_FILE = 'trades.csv'

# Ensure the CSV file exists and has the correct headers
if not os.path.isfile(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['order_id', 'ticker', 'buy_strike_price', 'buy_real_price', 'sell_real_price',
                         'buy_time', 'sell_time', 'order_type'])


def convert_utc_to_ist(utc_time_str):
    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    ist_time = utc_time.astimezone(pytz.timezone('Asia/Kolkata'))
    return ist_time.strftime("%Y-%m-%d %H:%M:%S")


def log_trade(order_id, ticker, buy_price, actual_price, buy_time, order_type):
    with open(CSV_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([order_id, ticker, buy_price, actual_price, '', buy_time, '', order_type])
    logger.info(f"Logged trade: Order ID: {order_id}, Ticker: {ticker}, Buy Price: {buy_price}, Actual Price: {actual_price}, Buy Time: {buy_time}, Order Type: {order_type}")


def update_trade(order_id, sell_price, sell_time):
    rows = []
    updated = False
    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)
        for row in reader:
            if row[0] == order_id and row[4] == '' and not updated:
                row[4] = sell_price
                row[6] = sell_time
                updated = True
            rows.append(row)

    with open(CSV_FILE, 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(header)
        csv_writer.writerows(rows)

    if updated:
        logger.info(f"Updated trade: Order ID: {order_id}, Sell Price: {sell_price}, Sell Time: {sell_time}")
    else:
        logger.warning(f"Trade not found for update: Order ID: {order_id}")


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
    order_id = data.get('order_id')
    ticker = data.get('ticker')
    timenow_utc = data.get('timenow')
    timenow_ist = convert_utc_to_ist(timenow_utc)
    actual_price = float(data.get('strategy.order.price'))
    action = data.get('strategy.order.action')
    comment = data.get('strategy.order.comment')

    if action == "buy":
        if comment == 'BuyCE':
            price = int(int(actual_price / 100) * 100)
        else:
            price = int((int(actual_price / 100) + 1) * 100)
        log_trade(order_id, ticker, price, actual_price, timenow_ist, comment)
    else:
        update_trade(order_id, actual_price, timenow_ist)

    return jsonify({'status': 'success'}), 200


if __name__ == '__main__':
    app.run(port=5000)
