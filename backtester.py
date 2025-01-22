from collections.abc import Callable
from typing import Optional

from pandas import DataFrame, to_datetime, read_csv
from numpy import nan
import os

from api.binanceApi import fetch_klines
from constants import market_his_dir_path


def backtest(
        eval_func: Callable,
        ticker: str,
        days: int = 14,
        interval: str = "1m",
        maker_fee: float = 0.00075,
        taker_fee: float = 0.00075,
        sell_limit: float = -0.75,
        buy_limit: float = 0.75,
        trade_long=True,
        trade_short=True,
        leverage: int = 1,
        use_csv: bool = False
):
    file_path = f"{market_his_dir_path}/{ticker}_{days}_{interval}.csv"
    if not os.path.isfile(file_path):
        print(f"{file_path} does not exist. Fetching data from Binance API...")
        use_csv = False

    if use_csv:
        df: DataFrame = read_csv(f"{market_his_dir_path}/{ticker}_{days}_{interval}.csv")
        df['timestamp'] = to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

    else:
        df: DataFrame = fetch_klines(ticker, interval, days=days)
        df.to_csv(f"{market_his_dir_path}/{ticker}_{days}_{interval}.csv")

    base_liquidity: float = 100
    balance: float = 100

    maker_fee_cost: float = 0.0
    taker_fee_cost: float = 0.0

    # List to store each iteration's relevant information
    bt_data = []

    last_traded_price: Optional[float] = None
    position: Optional[str] = None

    def get_liquidity():
        percentage_change: float = ((df.iloc[i]["Close"] / last_traded_price) - 1) * leverage \
            if last_traded_price is not None else 0

        if position == "long":
            return (balance * (1 + percentage_change)) / base_liquidity
        elif position == "short":
            return (balance * (1 - percentage_change)) / base_liquidity
        else:
            return balance / base_liquidity

    for i in range(len(df)):
        confidence: float = eval_func(df.iloc[0:i])

        cycle_info = {
            "timestamp": df.index[i],
            "confidence": confidence,
            "type": nan,  # Order type will be updated when an order is placed
            "price": nan,
            "fee": nan,
            "liquidity": nan
        }

        if confidence <= sell_limit:
            trade_made: bool = False
            price: float = df["Close"].iloc[i]

            if trade_long and position == "long":
                # Close long position
                percentage_change: float = ((price / last_traded_price) - 1) * leverage \
                    if last_traded_price is not None else 0
                percentage_change = 1 + percentage_change

                maker_fee_cost = balance * percentage_change * maker_fee
                balance = balance * percentage_change - maker_fee_cost

                position = None
                trade_made = True

            if trade_short and position != "short":
                # Create short position
                taker_fee_cost = balance * taker_fee
                balance = balance - taker_fee_cost
                last_traded_price = price

                position = "short"
                trade_made = True

            if trade_made:
                # Update cycle_info for a sell order
                cycle_info.update({
                    "type": "sell",
                    "price": price,
                    "fee": maker_fee_cost + taker_fee_cost
                })

        elif confidence >= buy_limit:
            trade_made: bool = False
            price: float = df["Close"].iloc[i]

            if trade_short and position == "short":
                # Close short position
                percentage_change: float = ((price / last_traded_price) - 1) * leverage \
                    if last_traded_price is not None else 0
                percentage_change = 1 - percentage_change

                taker_fee_cost = balance * percentage_change * taker_fee
                balance = balance * percentage_change - taker_fee_cost

                position = None
                trade_made = True

            if trade_long and position != "long":
                # Create long position
                maker_fee_cost = balance * maker_fee
                balance = balance - maker_fee_cost
                last_traded_price = price

                position = "long"
                trade_made = True

            if trade_made:
                # Update cycle_info for a buy order
                cycle_info.update({
                    "type": "buy",
                    "price": price,
                    "fee": maker_fee_cost + taker_fee_cost
                })

        # Append the current iteration's data to bt_data list
        cycle_info.update({
            "liquidity": get_liquidity()
        })

        bt_data.append(cycle_info)

        # Print status
        print(f"{(i + 1) / len(df):.2%} || CONF: {confidence:.2%} || BAL: {balance:.2f}")

    # Convert bt_data list to DataFrame
    bt_df = DataFrame(bt_data)

    # Convert the 'timestamp' column to datetime type and set it as the index
    bt_df['timestamp'] = to_datetime(bt_df['timestamp'])
    bt_df.set_index('timestamp', inplace=True)

    # Save to CSV
    bt_df.to_csv(f"{market_his_dir_path}/{ticker}_{days}_{interval}_orders.csv")

    return df, bt_df