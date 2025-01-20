from fileHandler import read_from_csv, write_to_csv
from backtester import backtest
from tradingComponents.indicators import RelativeStrengthIndex
from dataAnalysis import analyze

headers = [
    "timestamp",
    "type",
    "price",
    "fee",
    "confidence"
]

ticker = "BTCUSDT"
days = 14
interval = "1h"
balance=10000
sell_limit = -0.75
buy_limit = 0.75
maker_fee = 0.00075
taker_fee = 0.00075

tc = RelativeStrengthIndex(
    period=14,
    lower_band=30,
    upper_band=80,
    dynamic_return=True
)

def main():
    his_df, bt_df = backtest(
        tc.evaluate,
        ticker=ticker,
        days=days,
        interval=interval,
        balance=balance,
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        maker_fee=maker_fee,
        taker_fee=taker_fee
    )

    # Plot X and Y are placeholders for defining what to plot
    analyze(
        target_filename=ticker + "_" + str(days) + "_" + interval + ".csv",
        his_df=his_df,
        bt_df=bt_df,
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        display_volume=True,
        plot_liquidity=True,
        plot_orders=True,
        plot_limits=True,
        plot_conf=True
    )

if __name__ == "__main__":
    main()