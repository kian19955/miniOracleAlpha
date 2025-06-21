import time
import os

from binance import SIDE_BUY, SIDE_SELL, Client

import api.binanceAPI
from api.binanceAPI import place_future_order, cancel_order, close_open_position

test_key = os.getenv("BINANCE_TEST_KEY")
test_secret = os.getenv("BINANCE_TEST_SECRET")
test_client = Client(test_key, test_secret, testnet=True)

api.binanceAPI.client = test_client

def get_BTC_price() -> float:
    ticker_info = test_client.futures_symbol_ticker(symbol="BTCUSDT")
    return float(ticker_info['price'])

def test_place_order_none_params():
    """Test placing an order with amount=None and price=None (should use market order logic)."""
    print("Testing order placement with amount=None and price=None (Market Order)...")
    try:
        # Explicitly pass None for amount and price
        order = place_future_order(SIDE_BUY, "BTCUSDT")
        print("Order response:", order)
    except Exception as e:
        print("Test failed (None params):", e)

def test_place_order_market_with_amount():
    """Test placing a market order by omitting amount and price."""
    print("Testing market order placement (with amount defined)...")
    try:
        order = place_future_order(SIDE_BUY, "BTCUSDT", amount=0.01)
        print("Market Order response:", order)
    except Exception as e:
        print("Market order test failed:", e)

def test_place_order_market_with_price():
    """Test placing a limit order with explicit amount and price."""
    print("Testing market order placement (with price defined) ...")
    try:
        price = get_BTC_price() + 10
        print(f"Opening Order with price: {price}")

        order = place_future_order(SIDE_SELL, "BTCUSDT", price=price)
        print("Limit Order response:", order)
    except Exception as e:
        print("Limit order test failed:", e)

def test_cancel_single_order():
    """Test canceling a single order."""
    print("Testing cancellation of a single order...")
    try:
        # Place an order to cancel
        order = place_future_order(SIDE_BUY, "BTCUSDT", amount=0.01, price=get_BTC_price() / 2)
        print("Order placed for cancellation:", order)
        time.sleep(2)  # Allow time for the order to be registered
        cancel_order(order_id=order['orderId'], ticker="BTCUSDT")
        print("Successfully cancelled order with id:", order['orderId'])
    except Exception as e:
        print("Cancel single order test failed:", e)

def test_cancel_all_orders():
    """Test canceling all orders for BTCUSDT."""
    print("Testing cancellation of all orders for BTCUSDT...")
    try:
        # Place two orders to have multiple orders for cancellation
        order1 = place_future_order(SIDE_BUY, "BTCUSDT", amount=0.01, price=get_BTC_price() / 2)
        order2 = place_future_order(SIDE_SELL, "BTCUSDT", amount=0.01, price=get_BTC_price() * 2)
        print("Orders placed for cancellation:", order1, order2)
        time.sleep(2)
        cancel_order(ticker="BTCUSDT", cancel_all=True)
        print("Successfully cancelled all orders for BTCUSDT")
    except Exception as e:
        print("Cancel all orders test failed:", e)

def test_close_open_position():
    """Test closing an open_pos position for BTCUSDT."""
    print("Testing closing open_pos position for BTCUSDT...")
    try:
        close_open_position("BTCUSDT", position_side=SIDE_BUY)
        print("Closed position")
    except Exception as e:
        print("Close open_pos position test failed:", e)

if __name__ == "__main__":
    test_place_order_none_params()
    input()
    test_place_order_market_with_amount()
    input()
    test_place_order_market_with_price()
    input()
    test_cancel_single_order()
    input()
    test_cancel_all_orders()
    input()
    test_close_open_position()
    input()
    test_place_order_none_params()
    time.sleep(3)
    test_close_open_position()
