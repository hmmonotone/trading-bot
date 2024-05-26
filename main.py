from flask import Flask, request, jsonify
from datetime import datetime
import pytz
import csv
import os

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
        writer.writerow(['ticker', 'buy_strike_price', 'buy_real_price', 'sell_real_price',
                         'buy_time', 'sell_time', 'order_type'])


def convert_utc_to_ist(utc_time_str):
    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    ist_time = utc_time.astimezone(pytz.timezone('Asia/Kolkata'))
    return ist_time.strftime("%Y-%m-%d %H:%M:%S")


def log_trade(ticker, buy_price, actual_price, buy_time, order_type):
    with open(CSV_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([ticker, buy_price, actual_price, '', buy_time, '', order_type])


def update_trade(ticker, sell_price, sell_time):
    rows = []
    updated = False
    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)
        for row in reader:
            if row[0] == ticker and row[3] == '' and not updated:
                row[3] = sell_price
                row[5] = sell_time
                updated = True
            rows.append(row)

    with open(CSV_FILE, 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(header)
        csv_writer.writerows(rows)


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(f"Received data: {data}")

    # Extract data from webhook
    ticker = data.get('ticker')
    timenow_utc = data.get('timenow')
    timenow_ist = convert_utc_to_ist(timenow_utc)
    actual_price = float(data.get('strategy.order.price'))
    action = data.get('strategy.order.action')
    comment = data.get('strategy.order.comment')

    if action == "buy":
        if comment == 'BuyCE':
            price = int(int(actual_price/100)*100)
        else:
            price = int((int(actual_price/100)+1) * 100)
        log_trade(ticker, price, actual_price, timenow_ist, comment)
    else:
        update_trade(ticker, actual_price, timenow_ist)

    return jsonify({'status': 'success'}), 200


if __name__ == '__main__':
    app.run(port=80)
