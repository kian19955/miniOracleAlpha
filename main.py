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

ticker = "ETHUSDT"
days = 31
interval = "1h"
sell_limit = -0.55
buy_limit = 0.55
maker_fee = 0.00075
taker_fee = 0.00075

trade_long = True
trade_short = False

tc = RelativeStrengthIndex(
    period=14,
    lower_band=30,
    upper_band=80,
    rsi_as_signal=False
)

def main():
    his_df, bt_df = backtest(
        tc.evaluate,
        ticker=ticker,
        days=days,
        interval=interval,
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        maker_fee=maker_fee,
        taker_fee=taker_fee,
        trade_long=trade_long,
        trade_short=trade_short,
        leverage=2,
        use_csv=True
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
        plot_conf=True,
        plot_order_price_lines=True,
        trade_long=trade_long,
        trade_short=trade_short
    )

if __name__ == "__main__":
    main()