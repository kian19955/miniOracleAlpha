import atexit
from decimal import Decimal, ROUND_DOWN, getcontext
from typing import Optional

import keyboard
from binance.client import Client

# ----------Initialization----------
is_testnet: bool = False
if input("Use testnet? (y/n): ").lower().strip() == "y":
    API_KEY = input("Enter your Testnet Sessions API key: ")
    API_SECRET = input("Enter your Testnet Sessions API secret: ")
    is_testnet = True
else:
    import os
    from dotenv import load_dotenv

    load_dotenv()
    API_KEY = os.getenv("BINANCE_KEY")
    API_SECRET = os.getenv("BINANCE_SECRET")
    if API_KEY is None or API_SECRET is None:
        raise ValueError("Please set BINANCE_KEY and BINANCE_SECRET environment variables")

client = Client(API_KEY, API_SECRET, testnet=is_testnet)
active_balance: Optional[float] = None
symbol = input("Enter the trading symbol (e.g., BTCUSDT): ").upper().strip()


# ----------Helper Functions----------
def get_available_balance():
    """Retrieve available USDT balance from your Binance Futures account."""
    try:
        balances = client.futures_account_balance()
        for b in balances:
            if b['asset'] == 'USDT':
                return float(b['balance'])
    except Exception as e:
        print("Error retrieving account balance:", e)
    return None


def get_current_price():
    """Fetch the current last price for the given symbol."""
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        print("Error retrieving current price:", e)
    return None


def get_current_position():
    """Get current position info for the symbol."""
    try:
        positions = client.futures_position_information(symbol=symbol)
        for pos in positions:
            if pos['symbol'] == symbol:
                return pos
        return None
    except Exception as e:
        print("Error retrieving current position:", e)
        return None


def is_position_open():
    """Returns a tuple (True, position) if an open position exists, or (False, None) if no position is open."""
    pos = get_current_position()
    if pos and float(pos.get("positionAmt", 0)) != 0:
        return True, pos
    return False, None


def get_symbol_info(symbol):
    """Fetch symbol details (including filters) from Binance Futures."""
    try:
        exchange_info = client.futures_exchange_info()
        for s in exchange_info["symbols"]:
            if s["symbol"] == symbol:
                return s
        print(f"Symbol {symbol} not found in exchange info.")
        return None
    except Exception as e:
        print("Error retrieving exchange info:", e)
        return None


def get_precision_from_step_size(step_size):
    """Determine the number of decimal places allowed from the step size."""
    s = format(step_size, 'f').rstrip('0')
    if '.' in s:
        return len(s.split('.')[1])
    return 0


def clamp_quantity(quantity):
    """Clamp quantity to min/max limits and round to step size, without exceeding active balance."""
    precision = get_precision_from_step_size(step_size)
    getcontext().prec = 12
    quantizer = Decimal('1') if precision == 0 else Decimal(f'1e-{precision}')
    # Use ROUND_DOWN to avoid exceeding the balance
    clamped = float(Decimal(str(quantity)).quantize(quantizer, rounding=ROUND_DOWN))
    clamped = max(min_qty, min(max_qty, clamped))
    return clamped


def set_active_balance():
    global active_balance
    current_available_balance = get_available_balance()
    new_balance = 0
    try:
        new_balance = float(input(
            f"Enter the Active Balance (investment amount in USDT) for each trade (Current Active Balance: {active_balance}): "))
        if new_balance <= 0:
            print("Active Balance must be greater than 0.")
        elif current_available_balance is not None and new_balance > current_available_balance:
            print(
                f"Available balance ({current_available_balance} USDT) is less than the input Active Balance ({new_balance} USDT). Using available balance instead.")
            active_balance = current_available_balance
        else:
            active_balance = new_balance
            print(f"Active Balance set to {active_balance} USDT.")
    except ValueError as e:
        print(e)
        print(f"Please enter a valid number. Not {type(new_balance)}: {new_balance}")


# ----------Setup----------
symbol_info = get_symbol_info(symbol)
if symbol_info:
    step_size = None
    min_qty = None
    max_qty = None
    for f in symbol_info["filters"]:
        if f["filterType"] == "LOT_SIZE":
            step_size = float(f["stepSize"])
            min_qty = float(f["minQty"])
            max_qty = float(f["maxQty"])
    if step_size is None or min_qty is None or max_qty is None:
        raise ValueError(f"Necessary filters not found for symbol. {step_size=}, {min_qty=}, {max_qty=}")
else:
    raise ValueError(f"Symbol {symbol} not found in exchange info.")

while active_balance is None:
    set_active_balance()


# ----------Main Functions----------
def validate_order(func):
    """Decorator to calculate quantity and place order immediately, skipping if below step size."""

    def wrapper(*args, **kwargs):
        open_status, _ = is_position_open()
        if open_status:
            print("Position already open, cannot open a new one.")
            return

        available = get_available_balance()
        if available is None:
            print("Could not retrieve available balance.")
            return

        trade_balance = min(active_balance, available)
        if available < active_balance:
            print(
                f"Available balance ({available} USDT) is less than Active Balance ({active_balance} USDT). Using available balance.")

        current_price = get_current_price()
        if current_price is None:
            return

        # Calculate raw quantity
        raw_quantity = trade_balance / current_price

        # Check if raw quantity is less than step_size
        if raw_quantity < step_size:
            precision = get_precision_from_step_size(step_size)
            print(
                f"Calculated raw quantity {raw_quantity:.{precision}f} is less than step size {step_size}. "
                f"Rounding up would exceed active balance {trade_balance} USDT at price {current_price:.2f}. Order skipped."
            )
            return

        # Clamp quantity without exceeding balance
        trade_quantity = clamp_quantity(raw_quantity)

        precision = get_precision_from_step_size(step_size)
        print(
            f"Calculated order quantity: {trade_quantity:.{precision}f} for {trade_balance} USDT at price {current_price:.2f} (Step size: {step_size})")
        return func(*args, trade_quantity=trade_quantity, **kwargs)

    return wrapper


@validate_order
def open_long(trade_quantity):
    print()
    print("Attempting to open long position...")
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side='BUY',
            type='MARKET',
            quantity=trade_quantity
        )
        print("Long order executed:", order)
    except Exception as e:
        print("Error opening long position:", e)


@validate_order
def open_short(trade_quantity):
    print()
    print("Attempting to open short position...")
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side='SELL',
            type='MARKET',
            quantity=trade_quantity
        )
        print("Short order executed:", order)
    except Exception as e:
        print("Error opening short position:", e)


def close_position():
    print()
    print("Attempting to close position...")
    open_status, pos = is_position_open()
    if not open_status:
        print("No open position to close.")
        return

    position_amt = float(pos.get("positionAmt", 0))
    print("Closing position...")
    try:
        if position_amt > 0:
            order = client.futures_create_order(
                symbol=symbol,
                side='SELL',
                type='MARKET',
                quantity=abs(position_amt),
                reduceOnly=True
            )
        elif position_amt < 0:
            order = client.futures_create_order(
                symbol=symbol,
                side='BUY',
                type='MARKET',
                quantity=abs(position_amt),
                reduceOnly=True
            )
        print("Close order executed:", order)
    except Exception as e:
        print("Error closing position:", e)


# ----------Main Loop----------
keyboard.add_hotkey('right', open_long, suppress=True)
keyboard.add_hotkey('left', open_short, suppress=True)
keyboard.add_hotkey('down', close_position, suppress=True)
keyboard.add_hotkey('s', set_active_balance, suppress=True)

print("Hotkeys registered: Right Arrow for Long, Left Arrow for Short, Down Arrow to Close, S to Set Active Balance.")
print("----------Info----------")
print(f"Symbol: {symbol}")
print(f"Active Balance: {active_balance}")
print()
print("Keyboard Shortcuts:")
print("- Right Arrow: Open Long")
print("- Left Arrow: Open Short")
print("- Down Arrow: Close Position")
print("- S: Set Active Balance")
print("Press 'Q' to exit.")

atexit.register(close_position)
keyboard.add_hotkey('q', lambda: exit() if get_current_position() is None else print(
    "Cannot exit while a position is open."), suppress=True)

keyboard.wait('e')
print("Exiting program.")