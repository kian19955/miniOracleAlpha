import pandas as pd

from indicators.bollingerBands import bollinger_bands
from indicators.rsi import calculate_rsi_ema
from patterns.S_R_lines import support_and_resistance
from strategies.BB_RSI_Lines import find_closest_line, execute_trade

t=0
i=0
n=0
m=0
l=[]
tickers = ["BTCUSDT"]  # لیست تیکرها
portfolio = {ticker: {"balance": 10000, "coin": 0, "buy_price": None} for ticker in tickers}

def fetch(i):
    data = pd.read_csv("historical_data.csv")
    return data.iloc[i:400+i]

while t<8321 :
    print(i)
    for ticker in tickers:

        # Fetch data and calculate indicators
        data =fetch(i)
        if t%720 == 0:
            if portfolio["BTCUSDT"]["coin"] != 0:
                l.append(portfolio["BTCUSDT"]["coin"] * data["Close"].iloc[-1])
            else: l.append(portfolio["BTCUSDT"]["balance"])
        if t == 8320:
            if portfolio["BTCUSDT"]["coin"] != 0:
                print(portfolio["BTCUSDT"]["coin"] * data["Close"].iloc[-1],n,m)
            else:print(portfolio["BTCUSDT"]["balance"],n,m)
            print(l)

        coin =portfolio[ticker]["coin"]
        balance =portfolio[ticker]["balance"]

        BB = bollinger_bands(data, 20)
        data['RSI'] = calculate_rsi_ema(data['Close'], period=14)
        Rsi = data['RSI'].iloc[-1]
        lines = support_and_resistance(data, 15)
        last_price = data['Close'].iloc[-1]
        nearst_line = find_closest_line(lines, last_price)
        if coin ==0 :
            last_order_type ="sell"
        elif balance==0 :
            last_order_type = "buy"

        # Execute trade
        response = execute_trade(last_price, Rsi, nearst_line, last_order_type, BB.iloc[-1], lines,[1.5,1,0.5],portfolio[ticker]["buy_price"])
        if response[0] == "sell":
            portfolio[ticker]["balance"]=coin*data["Close"].iloc[-1]
            portfolio[ticker]["coin"]=0
            print("sell",portfolio)
            n +=1
        elif response[0] == "sellSL":
            portfolio[ticker]["balance"]=coin*data["Close"].iloc[-1]
            portfolio[ticker]["coin"]=0
            print("sellSL",portfolio)
            m +=1
        elif response[0] == "buy":

            portfolio[ticker]["coin"]=balance/data["Close"].iloc[-1]
            portfolio[ticker]["balance"] = 0
            print("buy",portfolio)



        # Print trade info if applicable
        if response[0]!=None:
            print(response)
        else:pass
            #print("nothing happend")
    i +=1
    t +=1
