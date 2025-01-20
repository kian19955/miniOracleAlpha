import requests
from datetime import datetime, timedelta
import pandas as pd

from TK import Token
from navidIsGod.api.utils import write_to_csv
from navidIsGod.constants import rel_market_his_dir_path

API_TOKEN = Token  # توکن خود را جایگزین کنید
BASE_URL = "https://api.nobitex.ir"
headers = {
    "Authorization": f"Token {API_TOKEN}"
}


def fetch_historical_data(ticker, interval, days, save_to_csv=True):
    now = datetime.now()
    start_time = now - timedelta(days=days)
    start_timestamp = int(start_time.timestamp())
    end_timestamp = int(now.timestamp())

    url = f"{BASE_URL}/market/udf/history"
    params = {
        "symbol": ticker,
        "resolution": interval,
        "from": start_timestamp,
        "to": end_timestamp
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if "t" in data and "c" in data and len(data["t"]) > 0:
            df = pd.DataFrame({
                "timestamp": data["t"],
                "Open": data["o"],
                "High": data["h"],
                "Low": data["l"],
                "Close": data["c"]
            })
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')

            if save_to_csv:
                csv_path = f"{rel_market_his_dir_path}/{ticker}_{days}_{interval}.csv"
                df.to_csv(csv_path, index=True)

            return df
        else:
            raise ValueError(f"Invalid or empty data returned from API for {ticker}. Data: {data}")
    else:
        raise Exception(f"Failed to fetch data for {ticker}. Status code: {response.status_code}")

def get_wallet(ticker: str | None = None,):
    url = f"{BASE_URL}/users/wallets/list"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Parse JSON response
        data = response.json()

        # Check if the response status is "ok"
        if data.get("status") == "ok":
            wallets = data.get("wallets", [])

            # Create a dictionary of wallets
            wallets_dict = {}
            for wallet in wallets:
                currency = wallet.get("currency", "Unknown")
                wallets_dict[currency] = {
                    "balance": wallet.get("balance", "0"),
                    "active_balance": wallet.get("activeBalance", "0"),
                    "deposit_address": wallet.get("depositAddress", "N/A"),
                }
            return wallets_dict
        else:
            print("Error: Response status is not 'ok'.")
            return {}
    else:
        print(f"Error {response.status_code}: {response.text}")
        return {}

    # Call the function and print the result

CSV_FILE = "wallet_data.csv"
def flatten_wallet_data(data):
    """داده‌های کیف پول را تخت کرده و به یک دیکشنری ساده تبدیل می‌کند."""
    flattened_data = {}
    for currency, details in data.items():
        flattened_data[f"{currency}_balance"] = details["balance"]
        flattened_data[f"{currency}_active_balance"] = details["active_balance"]
    return flattened_data



def update_wallet():
    print("Starting wallet data collection...")

    try:
        wallet_data = get_wallet()
        if wallet_data:
            flattened_data = flatten_wallet_data(wallet_data)

            write_to_csv(flattened_data,CSV_FILE)
            print("Data written to CSV.")
        else:
            print("No wallet data fetched.")
    except Exception as e:
        print(f"Error in main loop: {e}")

if __name__ == "__main__":
    fetch_historical_data("BTCUSDT", "D", 1)
