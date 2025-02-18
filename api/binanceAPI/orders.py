from typing import Optional

from . import client


def get_open_orders(ticker: str):

    return client.futures_get_open_orders(symbol=ticker)
