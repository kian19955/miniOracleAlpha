from functools import partial
import keyboard
from api.binanceAPI import (
    place_future_order,
    close_open_position,
    cancel_order,
    get_open_positions,
    get_open_orders
)


def place_market_order(side, ticker):
    order = place_future_order(side=side, ticker=ticker)
    print(f"Market order placed: {order}")


def place_limit_order(side, ticker):
    try:
        price = input(f"Enter the price for the {side} order: ")
        amount = input(f"Enter the amount for the {side} order: ")

        if price:
            price = float(price)
        else:
            price = None
        if amount:
            amount = float(amount)
        else:
            amount = None

        order = place_future_order(side=side, ticker=ticker, amount=amount, price=price)
        print(f"Limit order placed: {order}")
    except ValueError as e:
        print(f"Invalid input. {e}.")


def close_positions_or_orders(ticker):
    open_orders = get_open_orders(ticker=ticker)
    if open_orders:
        cancel_order(ticker=ticker, cancel_all=True)
        print(f"Cancelled all open orders for {ticker}.")
    else:
        close_open_position(ticker=ticker)
        print(f"Closed open position for {ticker}.")


def has_open_positions_or_orders(ticker):
    open_positions = get_open_positions()
    open_orders = get_open_orders(ticker=ticker)
    return bool(open_positions or open_orders)


def main():
    ticker = input("Ticker: ").strip().upper()

    # Define key mappings
    keymap = {
        "left": partial(place_market_order, "SELL", ticker),
        "right": partial(place_market_order, "BUY", ticker),
        "shift+left": partial(place_limit_order, "SELL", ticker),
        "shift+right": partial(place_limit_order, "BUY", ticker),
        "down": partial(close_positions_or_orders, ticker),
    }

    print("Press 'left' to place a SELL market order.")
    print("Press 'right' to place a BUY market order.")
    print("Press 'Shift + left' to place a SELL limit order.")
    print("Press 'Shift + right' to place a BUY limit order.")
    print("Press 'down' to close positions or cancel orders.")
    print("Press 'e' to exit (only if no open positions or orders).")

    for key_combination, action in keymap.items():
        keyboard.add_hotkey(key_combination, action)

    # Handle 'esc' key separately to allow safe exit
    keyboard.add_hotkey('e', lambda: exit() if not has_open_positions_or_orders(ticker) else print(
        "Cannot exit: Open positions or orders exist.")
    )

    print("Listening for key presses...")
    keyboard.wait()


if __name__ == "__main__":
    main()
