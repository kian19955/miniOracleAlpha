from collections.abc import Callable

from pandas import DataFrame, to_datetime
from numpy import nan

from navidIsGod.api.binanceApi import fetch_klines
from navidIsGod.constants import market_his_dir_path

def backtest(
        eval_func: Callable,
        ticker: str,
        days: int = 14,
        interval: str = "1m",
        balance: int = 10000,
        maker_fee: float = 0.00075,
        taker_fee: float = 0.00075,
        sell_limit: float = -0.75,
        buy_limit: float = 0.75
):
    df: DataFrame = fetch_klines(ticker, interval, days=days)
    df.to_csv(f"{market_his_dir_path}/{ticker}_{days}_{interval}.csv")
    base_liquidity: float = balance
    balance: int = balance

    assets: float = 0.0

    # List to store each iteration's relevant information
    bt_data = []

    for i in range(len(df)):
        confidence: float = eval_func(df.iloc[0:i])

        order_info = {
            "timestamp": df.index[i],
            "confidence": confidence,
            "type": nan,  # Order type will be updated when an order is placed
            "price": nan,
            "fee": nan,
            "liquidity": (balance + assets * df["Close"].iloc[i]) / base_liquidity,
        }

        if confidence <= sell_limit and assets > 0:
            price: float = df["Close"].iloc[i]
            fee = assets * price * maker_fee
            balance += assets * price - fee
            assets = 0

            # Update order_info for a sell order
            order_info.update({
                "type": "sell",
                "price": price,
                "fee": fee
            })

        elif confidence >= buy_limit and balance > 0:
            price: float = df["Close"].iloc[i]
            fee = balance * taker_fee
            assets += (balance - fee) / price
            balance = 0

            # Update order_info for a buy order
            order_info.update({
                "type": "buy",
                "price": price,
                "fee": fee
            })

        # Append the current iteration's data to bt_data list
        bt_data.append(order_info)

        # Print status
        print(f"{(i + 1) / len(df):.2%} || CONF: {confidence:.2%} || BAL: {balance:.2f} || ASSET: {assets:.2f}")

    # Convert bt_data list to DataFrame
    bt_df = DataFrame(bt_data)

    # Convert the 'timestamp' column to datetime type and set it as the index
    bt_df['timestamp'] = to_datetime(bt_df['timestamp'])
    bt_df.set_index('timestamp', inplace=True)

    # Save to CSV
    bt_df.to_csv(f"{market_his_dir_path}/{ticker}_{days}_{interval}_orders.csv")

    return df, bt_df