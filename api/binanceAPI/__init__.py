import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("BINANCE_KEY")
secret = os.getenv("BINANCE_SECRET")

if key is None or secret is None:
    raise ValueError("Please set BINANCE_KEY and BINANCE_SECRET environment variables")

from binance.client import Client

client = Client(key, secret)

# -------TestNet---------------------
if True:
    test_key = os.getenv("BINANCE_TEST_KEY")
    test_secret = os.getenv("BINANCE_TEST_SECRET")
    test_client = Client(test_key, test_secret, testnet=True)

    client = test_client
# ----------------------------------

from .fetching import fetch_klines, fetch_ticker_price, fetch_exchange_info
from .trading import place_future_order, cancel_order, close_open_position
from .orders import get_open_orders
from .positions import get_open_positions
from .websockets import track_orders
from .enums import EventType