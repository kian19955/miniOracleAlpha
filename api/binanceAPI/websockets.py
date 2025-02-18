from enum import EnumType
from typing import Optional

from binance import ThreadedWebsocketManager

from api.binanceAPI import client
from .enums import EventType
from api.utils.binanceStrUtils import flatten_dict


def track_orders(testnet: bool = False, whitelist: Optional[list[EventType]] = None):
    def handle_message(msg, whitelist=None):
        # Flatten the message dictionary
        flat_msg = flatten_dict(msg)

        filtered_info = {}

        for code, value in flat_msg.items():
            short_code = code.split('.')[-1]
            description = EventType.from_code(short_code) or code

            if whitelist is None or description in whitelist:
                filtered_info[description] = value

        print(f"Filtered Order Update: {filtered_info}")

    twm = ThreadedWebsocketManager(client.API_KEY, client.API_SECRET, testnet=testnet)
    twm.start()

    twm.start_futures_user_socket(callback=handle_message)
