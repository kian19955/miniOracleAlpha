import logging

import requests

from TK import Token
from navidIsGod.api.utils import write_to_csv

API_TOKEN = Token  # توکن خود را جایگزین کنید
BASE_URL = "https://api.nobitex.ir"
CSV_FILE = "orders_data.csv"

def place_order(order_type, ticker, amount, price) :

    src_currency,dst_currency  = ticker.split("USDT")[0].lower(), "usdt"
    url = f"{BASE_URL}/market/orders/add"
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "content-type": "application/json"
    }
    payload = {
        "type": order_type,
        "srcCurrency": src_currency,
        "dstCurrency": dst_currency,
        "amount": str(amount),
        "price": float(price),
        "clientOrderId": "order1"

    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()

        if data.get("status") == "ok":
            logging.info(f"Order placed successfully: {data}")
            write_to_csv({"type": order_type, "ticker": ticker, "amount": amount, "price": price}, CSV_FILE)
            return data
        else:
            logging.error(f"Failed to place order: {data}")
            return None
    else:
        logging.error(f"Failed to place order. Status code: {response.status_code}")
        return None


