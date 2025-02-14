from backtester import backtest
from tradingComponents.indicators import RelativeStrengthIndex, Stochastic, MovingAverageConvergenceDivergence
from custom_logger import setup_logger
from logging import DEBUG, getLogger

setup_logger('oracle.analysis', DEBUG, './logs/analysis.jsonl', log_in_json=True, stream_in_color=True)

ticker = "BTCUSDT"
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

ta = {
        "dna": {
            "fast_period": 72,
            "signal_line_period": 3,
            "momentum_max_lookback": 54,
            "momentum_signal_weight": 0.6467858832912314,
            "crossover_return_weight": False,
            "crossover_max_gradient_degree": 40.445516740719775,
            "crossover_gradient_signal_weight": 0.0,
            "crossover_weight_impact": 0.7083723426128932,
            "zero_line_crossover_weight": 1.0,
            "zero_line_pullback_lookback": 2,
            "zero_line_pullback_tolerance_percent": 0.9230176486212315,
            "zero_line_pullback_weight": 0.2432921076777589,
            "return_pullback_strength": False,
            "magnitude_weight": 0.0,
            "rate_of_change_weight": 0.3677107923240543,
            "weight_impact": 0.5902063182726573,
            "slow_period": 84
        },
        "stops": {
            "stop_loss": 0.020521404268725052,
            "take_profit": 0.008501729458850776
        }
    }

datasets={
            0: {
                'days': 93,
                'interval': '5m',
                'ticker': "SOLUSDT",
                'start': '2024-09-30 00:00:00',
            },
            1: {
                'days': 93,
                'ticker': "SOLUSDT",
                'interval': '5m',
                'start': '2024-07-02 00:00:00',
            },
            2: {
                'days': 93,
                'ticker': "SOLUSDT",
                'interval': '5m',
                'start': '2024-04-03 00:00:00',
            },
            3: {
                'days': 31,
                'ticker': 'DOGEUSDT',
                'interval': '5m',
                'start': "2023-09-01 00:00:00"
            }
        }

tc = MovingAverageConvergenceDivergence(
    **ta["dna"]
)


def main():
    stats, bt = backtest(
        tc.evaluate,
        fetch_kwargs=datasets[3],
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        commission=commission,
        trade_long=trade_long,
        trade_short=trade_short,
        leverage=leverage,
        use_csv=True,
        micro_factor=1000000,
        **ta["stops"]
    )
    print(stats)
    bt.plot(open_browser=False)

if __name__ == "__main__":
    main()
