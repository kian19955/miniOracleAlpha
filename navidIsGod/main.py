from fileHandler import read_from_csv, write_to_csv
from backtester import backtest
from tradingComponents import placeholder
from .dataAnalysis import analyze

headers = [
    "timestamp",
    "type",
    "price",
    "confidence"
]


def main():
    ticker = "BTCUSDT"
    days = 14
    interval = "1h"

    data = backtest(
        placeholder,
        ticker="BTCUSDT",
        days=14,
        interval="1h",
        balance=10000,
        sell_limit=-0.75,
        buy_limit=0.75,
        maker_fee=0.00075,
        taker_fee=0.00075
    )

    write_to_csv(
        headers=headers,
        data=data,
        filename=ticker + "_" + str(days) + "_" + interval + ".csv",
    )

    analyze(
        data=data,
    )

if __name__ == "__main__":
    main()