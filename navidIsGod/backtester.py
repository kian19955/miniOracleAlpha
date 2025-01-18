from typing import Type

from pandas import DataFrame

def backtest(
        tc: Type,
        ticker: str,
        days: int = 14,
        interval: str = "1m",
        balance: int = 10000,
        maker_fee: float = 0.00075,
        taker_fee: float = 0.00075,
        sell_limit: float = -0.75,
        buy_limit: float = 0.75
):
    balance: int = balance

    assets: float = 0.0

    total_fees = 0

    history_data: list = []
    def append_to_history(timestamp, order_type, asset_price, tc_confidence):
        data = [timestamp, order_type, asset_price, tc_confidence]
        history_data.append(data)

    for i in range(len(df)):
        confidence: float = tc.evaluate(df.iloc[0:i])

        if confidence <= sell_limit and assets > 0:
            price: float = df["Close"].iloc[i]

            fee = assets * price * maker_fee
            total_fees += fee
            balance += assets * price - fee

            assets = 0

            append_to_history(df.index[i], "sell", price, confidence)

        elif confidence >= buy_limit and balance > 0:
            price: float = df["Close"].iloc[i]

            fee = balance * taker_fee
            total_fees += fee

            assets += (balance - fee) / price
            balance = 0

            append_to_history(df.index[i], "buy", price, confidence)

    return history_data

