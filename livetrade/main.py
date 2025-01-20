import time

from SEPWallet import get_SEP_wallet, SEP_wallet_Update
from navidIsGod.api.NobitexApi import update_wallet, fetch_historical_data
from navidIsGod.tradingComponents.indicators.bollingerBands import bollinger_bands
from navidIsGod.tradingComponents.indicators.relativeStrengthIndex import calculate_rsi_ema
from orders import place_order
from navidIsGod.tradingComponents.strategies.BB_RSI_Lines import  execute_trade, find_closest_line
import pandas as pd
from navidIsGod.tradingComponents.patterns.S_R_lines import support_and_resistance


tickers = ["BTCUSDT"]
wallet_tickers=[ticker.lower().replace("usdt","") +"_active_balance" for ticker in tickers ]
SEP_wallet_Update()


while True:
    update_wallet()
    df = pd.read_csv("wallet_data.csv")
    latest_item = df.sort_values('timestamp')
    ordersdf= pd.read_csv("orders_data.csv")
    portfolio = {tw: {"balance": df[tw].iloc[-1]} for tw in wallet_tickers}
    print(portfolio)
    try:
        for ticker in tickers:

            filtered_orders = ordersdf[ordersdf["ticker"] == ticker]

            if not filtered_orders.empty:
                last_order = filtered_orders.sort_values("timestamp", ascending=False).iloc[0]
                last_order_type = last_order["type"]
                print(f"The last order type for {ticker} is: {last_order_type}")
            else:
                last_order_type ="sell"
                print(f"No orders found for {ticker} so its sell")

            try:
                # Fetch data and calculate indicators
                data = fetch_historical_data(ticker, "60", "15")
                BB = bollinger_bands(data,20)
                data['RSI'] = calculate_rsi_ema(data['Close'], period=14)
                Rsi = data['RSI'].iloc[-1]
                lines = support_and_resistance(data, 15)
                last_price = data['Close'].iloc[-1]
                nearst_line = find_closest_line(lines, last_price)

                # Execute trade
                response = execute_trade(last_price,Rsi, nearst_line,last_order_type,BB.iloc[-1],lines,[1,0,0],95000)
                if response == "sell1":
                    place_order("sell",ticker,portfolio[f"{ticker.lower().replace("usdt","") +"_active_balance"}"]["balance"],last_price-(last_price*0.0004))
                elif response == "buy1":
                    place_order("buy", ticker,
                                get_SEP_wallet(ticker.replace("USDT","-USDT")),
                                last_price+(last_price*0.0004))

                # Print the current status
                print(f"{ticker} - Price: {last_price:.4f}, RSI: {Rsi:.3f}, Balance: {portfolio[f"{ticker.lower().replace("usdt","") +"_active_balance"}"]["balance"]:.5f}")

                # Print trade info if applicable
                if response:
                    print(response)
                else : print("nothing happend")
            except Exception as e:

                print(f"Error processing {ticker}: {e}")

        time.sleep(60)  # Wait 60 seconds before the next iteration
    except KeyboardInterrupt:
        print("Process stopped by user.")
        break
