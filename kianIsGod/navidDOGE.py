import json
import time
import threading
import websocket
import numpy as np

# Binance WebSocket API Settings
WS_URL = "wss://stream.binance.com:9443/ws/dogeusdt@depth"
market = "DOGEUSDT"

# Strategy Settings
balance = 100.0
position = 0.0
entry_price = None
stop_loss = None
take_profit = None
trading_fee = 0.0005
leverage = 1
sl_percent = 0.0029
tp_percent = 0.0015
last_trade_time = 0

# Order Book Data
asks = np.array([])
bids = np.array([])
lock = threading.Lock()

# Global flag to indicate if we were disconnected.
was_disconnected = False

def on_message(ws, message):
    """Handle incoming Binance depth update messages."""
    global asks, bids
    data = json.loads(message)
    # For debugging purposes, you can uncomment the following line:
    # print("Received message:", data)
    if data.get("e") == "depthUpdate":
        with lock:
            new_asks = []
            for price, qty in data.get("a", []):
                qty = float(qty)
                if qty > 0:
                    new_asks.append([float(price), qty])
            new_bids = []
            for price, qty in data.get("b", []):
                qty = float(qty)
                if qty > 0:
                    new_bids.append([float(price), qty])
            if new_asks:
                asks = np.array(sorted(new_asks, key=lambda x: x[0]))
            if new_bids:
                bids = np.array(sorted(new_bids, key=lambda x: -x[0]))

def on_open(ws):
    global was_disconnected
    if was_disconnected:
        on_reconnect()
        was_disconnected = False
    print("Connected to Binance depth stream for", market)

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    global was_disconnected
    was_disconnected = True
    on_disconnect(ws, close_status_code, close_msg)
    print("Attempting to reconnect...")
    reconnect(ws)

def on_disconnect(ws, close_status_code, close_msg):
    """Custom disconnect handler."""
    print("WebSocket disconnected. Code:", close_status_code, "Message:", close_msg)

def on_reconnect():
    """Custom reconnect handler."""
    print("WebSocket reconnected!")

def reconnect(ws):
    """Attempt to reconnect after a disconnect."""
    time.sleep(5)  # Wait 5 seconds before attempting to reconnect.
    new_ws = websocket.WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_open=on_open,
        on_error=on_error,
        on_close=on_close,
    )
    new_ws_thread = threading.Thread(target=lambda: new_ws.run_forever(ping_interval=20, ping_timeout=10))
    new_ws_thread.daemon = True
    new_ws_thread.start()

def calculate_imbalance():
    with lock:
        if asks.size == 0 or bids.size == 0:
            return 0
        total_ask_volume = np.sum(asks[:, 1])
        total_bid_volume = np.sum(bids[:, 1])
        if total_bid_volume + total_ask_volume == 0:
            return 0
        return (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)

def execute_trade(side, price):
    global balance, position, entry_price, stop_loss, take_profit, last_trade_time
    if time.time() - last_trade_time < 1:
        return
    amount = balance * leverage / price
    if balance > 0:
        cost = amount * price / leverage
        balance -= cost
        if side == "LONG":
            position += amount
            entry_price = price
            stop_loss = entry_price * (1 - sl_percent)
            take_profit = entry_price * (1 + tp_percent)
            print(f"🟢 LONG {amount:.8f} DOGE @ {price:.8f} | SL: {stop_loss:.8f} | TP: {take_profit:.8f}")
        elif side == "SHORT":
            position -= amount
            entry_price = price
            stop_loss = entry_price * (1 + sl_percent)
            take_profit = entry_price * (1 - tp_percent)
            print(f"🔴 SHORT {amount:.8f} DOGE @ {price:.8f} | SL: {stop_loss:.8f} | TP: {take_profit:.8f}")
        last_trade_time = time.time()

def close_position(price):
    global balance, position, entry_price, stop_loss, take_profit, last_trade_time
    if position > 0:
        balance += position * price * (1 - trading_fee)
        print(f"🔵 Close LONG @ {price:.8f} | P/L: {(price - entry_price) * position:.8f} USDT")
    elif position < 0:
        balance += abs(position) * (2 * entry_price - price) * (1 - trading_fee)
        print(f"🟠 Close SHORT @ {price:.8f} | P/L: {(entry_price - price) * abs(position):.8f} USDT")
    position = 0.0
    entry_price = None
    stop_loss = None
    take_profit = None
    last_trade_time = time.time()

def high_frequency_trade():
    """Execute HFT trades and update user every ~10ms."""
    global position, stop_loss, take_profit, last_trade_time
    while True:
        start_time = time.time()
        with lock:
            if asks.size == 0 or bids.size == 0:
                time.sleep(0.005)
                continue
            best_ask = asks[0, 0]
            best_bid = bids[0, 0]
            last_price = (best_ask + best_bid) / 2
            spread = best_ask - best_bid
            imbalance = calculate_imbalance()
        print(f"\n✅ Price: {last_price:.6f} USDT")
        print(f"📊 Imbalance: {imbalance:.5f} | 📈 Spread: {spread:.8f}")
        if position != 0:
            pnl = (last_price - entry_price) * position if position > 0 else (entry_price - last_price) * abs(position)
            print(f"💹 Real-time PNL: {pnl:.5f} USDT")
            if (position > 0 and last_price >= take_profit) or (position < 0 and last_price <= take_profit):
                print("🎯 TP hit!")
                close_position(last_price)
            elif (position > 0 and last_price <= stop_loss) or (position < 0 and last_price >= stop_loss):
                print("⚠️ SL hit!")
                close_position(last_price)
        if position == 0 and time.time() - last_trade_time > 1:
            if imbalance > 0.3 and spread > 0.00001:
                execute_trade("LONG", best_ask)
            elif imbalance < -0.3 and spread > 0.00001:
                execute_trade("SHORT", best_bid)
        print(f"💰 Balance: {balance:.5f} USDT | 📉 Position: {position:.5f} DOGE")
        # Define a 10ms update interval:
        elapsed = time.time() - start_time
        sleep_duration = max(0.01 - elapsed, 0)
        time.sleep(sleep_duration)

def keyboard_listener():
    import keyboard  # Requires `pip install keyboard`
    while True:
        if keyboard.is_pressed("0"):
            with lock:
                if position != 0:
                    price = asks[0, 0] if position > 0 else bids[0, 0]
                    print("🛑 Manual Close Triggered!")
                    close_position(price)
                else:
                    print("❌ No open_pos position to close_pos.")
            time.sleep(0.2)

ws = websocket.WebSocketApp(
    WS_URL,
    on_message=on_message,
    on_open=on_open,
    on_error=on_error,
    on_close=on_close
)
ws_thread = threading.Thread(target=lambda: ws.run_forever(ping_interval=20, ping_timeout=10))
ws_thread.daemon = True
ws_thread.start()

trade_thread = threading.Thread(target=high_frequency_trade)
trade_thread.daemon = True
trade_thread.start()

keyboard_listener()
