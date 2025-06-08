from backtester import backtest
from tradingComponents.indicators import   MovingAverageConvergenceDivergence
from tradingComponents.strategies import ShadowsTrendingTouch
from custom_logger import setup_logger
from logging import DEBUG

setup_logger('oracle.analysis', DEBUG, './logs/analysis.jsonl', log_in_json=True, stream_in_color=True)

ticker = "BTCUSDT"

sell_limit = -0.75
buy_limit = 0.75

leverage = 5
commission = 0.00075

ta = {
    "dna": {
        "fast_period": 28,
        "signal_line_period": 30,
        "momentum_max_lookback": 17,
        "momentum_signal_weight": 0.734374324982434,
        "crossover_return_weight": False,
        "crossover_max_gradient_degree": 25.72682242872742,
        "crossover_gradient_signal_weight": 0.2399,
        "crossover_weight_impact": 0.33062400559960325,
        "zero_line_crossover_weight": 0.9987157290164548,
        "zero_line_pullback_lookback": 2,
        "zero_line_pullback_tolerance_percent": 0.3276036034958676,
        "zero_line_pullback_weight": 1.766904365264866e-08,
        "return_pullback_strength": False,
        "magnitude_weight": 0.7190869384548095,
        "rate_of_change_weight": 0.5458,
        "weight_impact": 0.6975590678566683,
        "slow_period": 63
    },
    "stops": {
        "stop_loss": 0.0,
        "take_profit": 0.0
    }
}

datasets={
            0: {
                'days': 1018,
                'interval': '15m',
                'ticker': "BTCUSDT",
                'start': "2020-01-01 00:00:00"
            },
            1: {
                'days': 365,
                'ticker': "SOLUSDT",
                'interval': '5m',
                'start': '2024-07-02 00:00:00',
            },
            2: {
                'days': 365,
                'ticker': "DOGEUSDT",
                'interval': '1h',
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
tc = ShadowsTrendingTouch(
    sma_period=7,
    shadow_to_body_ratio=1.25,
    shadow_padding_price=0,
    opposite_shadow_to_body_ratio=0.25
)

def main():
    stats, bt = backtest(
        tc.evaluate,
        fetch_kwargs=datasets[1],
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        commission=commission,
        trade_long=True,
        trade_short=True,
        stop_loss=0.0025,
        take_profit=0.01,
        leverage=leverage,
        use_csv=True,
        micro_factor=None,
    )
    print(stats)
    bt.plot(open_browser=False)

if __name__ == "__main__":
    main()
