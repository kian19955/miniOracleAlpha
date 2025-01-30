from backtester import backtest
from dataAnalysis.plotter import plot_data
from tradingComponents.indicators import RelativeStrengthIndex, Stochastic, MovingAverageConvergenceDivergence
from dataAnalysis import analyze
from custom_logger import setup_logger
from logging import DEBUG, getLogger

setup_logger('oracle.analysis', DEBUG, './logs/analysis.jsonl', log_in_json=True, stream_in_color=True)
headers = [
    "timestamp",
    "type",
    "price",
    "fee",
    "confidence"
]

ticker = "SOLUSDT"
days = 7
interval = "1m"
sell_limit = -0.75
buy_limit = 0.75
maker_fee = 0.00075
taker_fee = 0.00075

trade_long = True
trade_short = True
settings = {'fast_period': 42, 'slow_period': 90, 'signal_line_period': 24, 'momentum_max_lookback': 51,
 'momentum_signal_weight': 0.5578000000000001, 'crossover_return_weight': True,
 'crossover_max_gradient_degree': 88.03937584556466, 'crossover_gradient_signal_weight': 0.8212,
 'crossover_weight_impact': 0.1265, 'zero_line_crossover_weight': 0.998639817622752, 'zero_line_pullback_lookback': 19,
 'zero_line_pullback_tolerance_percent': 0.5487446218136476, 'zero_line_pullback_weight': 0.41714182779059517,
 'return_pullback_strength': True, 'magnitude_weight': 0.8083685289854661, 'rate_of_change_weight': 0.9985617455723734,
 'weight_impact': 0.4497}
settings = {'period': 17, 'lower_band': 3.550917741204702, 'upper_band': 73.09752054858266}

tc = RelativeStrengthIndex(
    **settings
)
"""tc = RelativeStrengthIndex(
    period=8,
    lower_band=7.48,
    upper_band=99.67000000000003,
    rsi_as_signal=False
)"""
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
        target_filename=ticker + "_" + str(days) + "_" + interval + ".csv",
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
        plot_limits=False,
        plot_conf=False,
        plot_order_price_lines=True
    )


if __name__ == "__main__":
    main()
