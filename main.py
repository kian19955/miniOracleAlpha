from backtester import backtest
from dataAnalysis.plotter import plot_data
from tradingComponents.indicators import RelativeStrengthIndex, Stochastic
from dataAnalysis import analyze

headers = [
    "timestamp",
    "type",
    "price",
    "fee",
    "confidence"
]

ticker = "SOLUSDT"
days = 165
interval = "1h"
sell_limit = -0.9
buy_limit = 0.9
maker_fee = 0.00075
taker_fee = 0.00075

trade_long = True
trade_short = True

tc = RelativeStrengthIndex(
    period=8,
    lower_band=7.48,
    upper_band=99.67000000000003,
    rsi_as_signal=False
)
"""
tc = Stochastic(
    lookback_period=14,
    smoothing_period=3,
    crossover_return_strength=False,
    crossover_max_gradient_degree=1,
    crossover_gradient_signal_weight=0,
    crossover_weight_impact=0,
    stochastic_weight=0,
    crossover_weight=1,
)
"""
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
        leverage=1,
        use_csv=True
    )

    # Plot X and Y are placeholders for defining what to plot
    analyze(
        target_filename = ticker + "_" + str(days) + "_" + interval + ".csv",
        bt_df=bt_df,
        trade_long=trade_long,
        trade_short=trade_short
    )

    plot_data(
        plot_title=ticker + "_" + str(days) + "_" + interval + ".csv",
        his_df=his_df,
        bt_df=bt_df,
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        display_volume=True,
        plot_liquidity=True,
        plot_orders=True,
        plot_limits=True,
        plot_conf=True,
        plot_order_price_lines=False
    )

if __name__ == "__main__":
    main()