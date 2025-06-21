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
    try:
        balances = client.futures_account_balance()
        for b in balances:
            if b['asset'] == 'USDT':
                return float(b['balance'])
        print("USDT balance not found.")
        return None
    except Exception as e:
        print("Error retrieving account balance:", e)
        return None

def get_current_price():
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        print("Error retrieving current price:", e)
        return None

def get_current_position():
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
    pos = get_current_position()
    if pos and float(pos.get("positionAmt", 0)) != 0:
        return True, pos
    return False, None

def get_symbol_info(symbol):
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
    s = format(step_size, 'f').rstrip('0')
    if '.' in s:
        return len(s.split('.')[1])
    return 0

def clamp_quantity(quantity):
    precision = get_precision_from_step_size(step_size)
    getcontext().prec = 12
    quantizer = Decimal('1') if precision == 0 else Decimal(f'1e-{precision}')
    clamped = float(Decimal(str(quantity)).quantize(quantizer, rounding=ROUND_DOWN))
    clamped = max(min_qty, min(max_qty, clamped))
    return clamped

def set_active_balance():
    global active_balance
    print("Setting active balance...")
    current_available_balance = get_available_balance()
    new_balance = 0
    try:
        new_balance = float(input(
            f"Enter the Active Balance (investment amount in USDT) for each trade (Current Active Balance: {active_balance}): "
        ).lstrip("asdbq").strip())
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
    print("Active balance setting complete.")

def set_ticker():
    global symbol
    symbol = input("Enter the trading symbol (e.g., BTCUSDT): ").upper().strip()
    print(f"Ticker set to {symbol}")

# ----------Main Functions----------
def validate_order(func):
    def wrapper(*args, **kwargs):
        print(f"Validating {func.__name__} order...")
        open_status, _ = is_position_open()
        if open_status:
            print("Position already open_pos, cannot open_pos a new one.")
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

        raw_quantity = trade_balance / current_price
        if raw_quantity < step_size:
            precision = get_precision_from_step_size(step_size)
            print(
                f"Calculated raw quantity {raw_quantity:.{precision}f} is less than step size {step_size}. "
                f"Rounding up would exceed active balance {trade_balance} USDT at price {current_price:.2f}. Order skipped."
            )
            return

        trade_quantity = clamp_quantity(raw_quantity)
        precision = get_precision_from_step_size(step_size)
        print(
            f"Calculated order quantity: {trade_quantity:.{precision}f} for {trade_balance} USDT at price {current_price:.2f} (Step size: {step_size})")
        result = func(*args, trade_quantity=trade_quantity, **kwargs)
        print(f"{func.__name__} validation complete.")
        return result

    return wrapper

@validate_order
def open_long(trade_quantity):
    print("Attempting to open_pos long position...")
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
    print("Attempting to open_pos short position...")
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
    print("Attempting to close_pos position...")
    open_status, pos = is_position_open()
    if not open_status:
        print("No open_pos position to close_pos.")
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
    print("Close position attempt complete.")

# ----------Setup----------
atexit.register(close_position)

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

# ----------Main Loop----------
print()
print("----------Info----------")
print(f"Symbol: {symbol}")
print(f"Active Balance: {active_balance}")
print()
print("Commands:")
print("- d: Open Long")
print("- a: Open Short")
print("- s: Close Position")
print("- b: Set Active Balance")
print("- v: Set Ticker")
print("Press 'q' to exit.")

if input("Use keyboard shortcuts? (y/n): ").lower().strip() == "y":
    keyboard.add_hotkey('d', open_long)
    keyboard.add_hotkey('a', open_short)
    keyboard.add_hotkey('s', close_position)
    keyboard.add_hotkey('b', set_active_balance)
    keyboard.add_hotkey('v', set_ticker)

    keyboard.add_hotkey('q', lambda: exit() if get_current_position() is None else print(
        "Cannot exit while a position is open_pos."), suppress=True)

    keyboard.wait('e')
    print("Exiting program.")
else:
    while True:
        choice = input("Enter your choice: ").strip()
        match choice:
            case "d":
                open_long()
            case "a":
                open_short()
            case "s":
                close_position()
            case "b":
                set_active_balance()
            case "v":
                set_ticker()
            case "q":
                exit() if get_current_position() is None else print("Cannot exit while a position is open_pos.")
            case _:
                print("Invalid choice. Please try again.")