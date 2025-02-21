from typing import Optional
import math

from binance import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT

from . import client


def place_future_order(side, ticker, amount=None, price=None):
    if side not in [SIDE_BUY, SIDE_SELL]:
        raise ValueError("Invalid order side. Must be 'BUY' or 'SELL'.")

    is_market_order = (price is None)

    # Fetch symbol information
    symbol_info = client.futures_exchange_info()
    symbol_data = next((item for item in symbol_info['symbols'] if item['symbol'] == ticker), None)
    if not symbol_data:
        raise ValueError(f"Symbol {ticker} not found.")

    filters = {f['filterType']: f for f in symbol_data['filters']}
    price_filter = filters.get('PRICE_FILTER')
    lot_size_filter = filters.get('LOT_SIZE')
    percent_price_filter = filters.get('PERCENT_PRICE')

    if not price_filter or not lot_size_filter:
        raise ValueError("Necessary filters not found for symbol.")

    tick_size = float(price_filter['tickSize'])
    step_size = float(lot_size_filter['stepSize'])
    min_price = float(price_filter['minPrice'])
    max_price = float(price_filter['maxPrice'])

    # PERCENT_PRICE filter: limits price movements relative to the market price
    if percent_price_filter:
        multiplier_up = float(percent_price_filter['multiplierUp'])
        multiplier_down = float(percent_price_filter['multiplierDown'])
    else:
        multiplier_up = 1
        multiplier_down = 1

    # Determine price
    if is_market_order:
        price = float(client.futures_symbol_ticker(symbol=ticker)["price"])
        print(f"Using current market price: {price}")
    else:
        if not isinstance(price, (float, int)):
            raise ValueError(f"Price must be a number not {type(price)}")
        if price < min_price or price > max_price:
            raise ValueError(f"Price must be between {min_price} and {max_price}.")

        # Check if price is within PERCENT_PRICE filter
        market_price = float(client.futures_symbol_ticker(symbol=ticker)["price"])
        upper_limit = market_price * multiplier_up
        lower_limit = market_price * multiplier_down

        if price < lower_limit or price > upper_limit:
            raise ValueError(f"Price must be within the range of {lower_limit} and {upper_limit} based on market price.")

        # Adjust price to the nearest tick size
        price = round(math.floor(price / tick_size) * tick_size, int(-math.log10(tick_size)))
        print(f"Adjusted price to nearest tick size: {price}")

    # Calculate amount based on balance if not provided
    if amount is None:
        balance_info = client.futures_account_balance()
        usdt_balance = float(next(item for item in balance_info if item['asset'] == 'USDT')['balance'])
        amount = usdt_balance / price
        print(f"Calculated amount based on available balance: {amount}")

    # Adjust amount to the nearest step size
    amount = round(math.floor(amount / step_size) * step_size, int(-math.log10(step_size)))
    print(f"Adjusted amount to nearest step size: {amount}")

    # Place the order
    order_params = {
        'symbol': ticker,
        'side': side,
        'quantity': amount,
        'type': ORDER_TYPE_MARKET if is_market_order else ORDER_TYPE_LIMIT
    }

    if not is_market_order:
        order_params['price'] = price
        order_params['timeInForce'] = 'GTC'

    try:
        order = client.futures_create_order(**order_params)
        print(f"Order placed successfully: {order}")
        return order
    except Exception as e:
        print(f"An error occurred while placing the order: {e}")
        return None


def cancel_order(ticker: str, order_id: Optional[int] = None, cancel_all: bool = False):
    if (order_id is None or ticker is None) and cancel_all is False:
        raise ValueError("Either order_id and ticker must be provided or cancel_all must be true.")

    if cancel_all:
        client.futures_cancel_all_open_orders(symbol=ticker)
        return

    client.futures_cancel_order(symbol=ticker, orderId=order_id)


def close_open_position(ticker: str, position_side: Optional[str] = None):
    closed_orders = []
    positions = client.futures_position_information(symbol=ticker)

    for position in positions:
        position_amt = float(position['positionAmt'])
        if position_amt == 0:
            continue

        if position_amt > 0 and (position_side in [SIDE_BUY, None]):
            order_side = SIDE_SELL
        elif position_amt < 0 and (position_side in [SIDE_SELL, None]):
            order_side = SIDE_BUY
        else:
            continue

        order = client.futures_create_order(
            symbol=ticker,
            side=order_side,
            type=ORDER_TYPE_MARKET,
            quantity=abs(position_amt),
            timeInForce="IOC",
            reduceOnly=True
        )
        closed_orders.append(order)

    return closed_orders
