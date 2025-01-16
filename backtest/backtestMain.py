import csv

import pandas as pd

from indicators.bollingerBands import bollinger_bands
from indicators.rsi import calculate_rsi_ema
from patterns.S_R_lines import support_and_resistance
from plugins import BBW_plugin
from strategies.BB_RSI_Lines import find_closest_line, execute_trade
import random
from deap import base, creator, tools, algorithms


def save_to_csv(file_name, price, response, value,bbu,bbl,sma):

    header = ["Price", "Response", "Value","BBU","BBL","SMA"]  # سرستون‌های فایل CSV

    try:
        # بررسی وجود فایل و ایجاد در صورت نیاز
        with open(file_name, mode='a', newline='') as file:
            writer = csv.writer(file)

            # اگر فایل تازه ایجاد شده باشد، سرستون‌ها را بنویس
            if file.tell() == 0:
                writer.writerow(header)

            # اضافه کردن داده‌ها
            writer.writerow([price, response, value,bbu,bbl,sma])


    except Exception as e:
        print(f"Error saving data to CSV: {e}")


def fetch(i):
    data = pd.read_csv("historical_data.csv")
    return data.iloc[i:400 + i]


def backtest(W):
    t = 0
    i = 0
    n = 0
    m = 0
    l = []
    tickers = ["BTCUSDT"]  # لیست تیکرها
    portfolio = {ticker: {"balance": 10000, "coin": 0, "buy_price": None} for ticker in tickers}
    csv_file = "plot_data.csv"

    while t < 8321:
        print(round(i / 8321 * 100, 2), " %")
        for ticker in tickers:
            if portfolio["BTCUSDT"]["coin"] != 0:
                value =portfolio["BTCUSDT"]["coin"] * data["Close"].iloc[-1]
            else:value=portfolio["BTCUSDT"]["balance"]
            # Fetch data and calculate indicators
            data = fetch(i)
            if t % 720 == 0:
                if portfolio["BTCUSDT"]["coin"] != 0:
                    l.append((portfolio["BTCUSDT"]["coin"] * data["Close"].iloc[-1]))
                    #portfolio["BTCUSDT"]["coin"] =0
                    #portfolio["BTCUSDT"]["balance"] = 10000
                else:
                    l.append((portfolio["BTCUSDT"]["balance"]))
                    #portfolio["BTCUSDT"]["balance"]=10000

            if t == 8320:
                if portfolio["BTCUSDT"]["coin"] != 0:
                    print("avg :", sum(l) / len(l))
                    print(l)
                    return (sum(l) / len(l))

                else:
                    print(l)
                    print("avg :", sum(l) / len(l))
                    return (sum(l) / len(l))

            coin = portfolio[ticker]["coin"]
            balance = portfolio[ticker]["balance"]

            BB = bollinger_bands(data, 20)
            data['RSI'] = calculate_rsi_ema(data['Close'], period=14)
            Rsi = data['RSI'].iloc[-1]
            lines = support_and_resistance(data, 15)
            last_price = data['Close'].iloc[-1]
            nearst_line = find_closest_line(lines, last_price)
            if coin == 0:
                last_order_type = "sell"
            elif balance == 0:
                last_order_type = "buy"

            # Execute trade

            strategy_response = execute_trade(last_price, Rsi, nearst_line, last_order_type, BB.iloc[-1], lines, W,
                                     portfolio[ticker]["buy_price"])
            response =BBW_plugin(BB["BBW"].iloc[-1],strategy_response)
            if response[0] == "sell":
                portfolio[ticker]["balance"] = coin * data["Close"].iloc[-1]
                portfolio[ticker]["coin"] = 0

                n += 1
            elif response[0] == "sellSL":
                portfolio[ticker]["balance"] = coin * data["Close"].iloc[-1]
                portfolio[ticker]["coin"] = 0

                m += 1
            elif response[0] == "buy":
                portfolio[ticker]["coin"] = balance / data["Close"].iloc[-1]
                portfolio[ticker]["balance"] = 0
                portfolio[ticker]["buy_price"] = response[1]

            save_to_csv(csv_file, last_price, response[0],value,BB["Bollinger_Upper"].iloc[-1],BB["Bollinger_Lower"].iloc[-1],BB["SMA"].iloc[-1])
            # Print trade info if applicable
            if response[0] != None:
                pass
                # print(response)
            else:
                pass
            # print("nothing happend")
        i += 1
        t += 1


backtest([1, 0, 0])
