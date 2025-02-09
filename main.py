from backtester import backtest
from tradingComponents.indicators import RelativeStrengthIndex, Stochastic, MovingAverageConvergenceDivergence
from custom_logger import setup_logger
from logging import DEBUG, getLogger

setup_logger('oracle.analysis', DEBUG, './logs/analysis.jsonl', log_in_json=True, stream_in_color=True)

ticker = "DOGEUSDT"
days = 93
interval = "5m"
sell_limit = -0.75
buy_limit = 0.75

leverage = 5
microfactor = 100000
commission = 0.00075

stop_loss = 0.9390000000000001
take_profit = 0.462

trade_long = True
trade_short = True
settings = {'period': 15, 'lower_band': 28.900000000000002, 'upper_band': 74.2}

bt_settings = {
    'days': 93,
    'interval': '5m',
    'ticker': "DOGEUSDT",
    'trade_long': True,
    'trade_short': True,
    'leverage': 5,
    'micro_factor': 100000,

}

tc = RelativeStrengthIndex(
    **settings
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
    stats, bt = backtest(
        tc.evaluate,
        ticker=ticker,
        days=days,
        interval=interval,
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        commission=commission,
        trade_long=trade_long,
        trade_short=trade_short,
        stop_loss=stop_loss,
        take_profit=take_profit,
        leverage=leverage,
        use_csv=True
    )
    print(stats)
    rades = stats._trades
    for equity in stats._equity_curve:
        print(equity)
    bt.plot(open_browser=False)

if __name__ == "__main__":
    main()
