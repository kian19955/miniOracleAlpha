import time

from binance import SIDE_BUY

from api.binanceAPI import get_open_orders, place_future_order, close_open_position, track_orders, EventType

def test_get_order():
    track_orders(testnet=True, whitelist=[EventType.CLIENT_ORDER_ID, EventType.ORDER_TYPE, EventType.ORDER_PRICE, EventType.CURRENT_ORDER_STATUS])
    ticker = "BTCUSDT"
    order_id = place_future_order(SIDE_BUY, ticker)["orderId"]
    time.sleep(1)
    print("Fetching Orders")
    print(get_open_orders(order_id=order_id, ticker=ticker))
    close_open_position("BTCUSDT", position_side=SIDE_BUY)


if __name__ == '__main__':
    test_get_order()