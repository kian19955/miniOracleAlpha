import os
from logging import DEBUG

from custom_logger import setup_logger
from paperTrading import PaperTrader

from tradingComponents.indicators import MovingAverageConvergenceDivergence

strat = MovingAverageConvergenceDivergence(
    fast_period=28,
    slow_period=90,
    signal_line_period=30,
    momentum_max_lookback=17,
    momentum_signal_weight=0.734374324982434,
    crossover_return_weight=False,
    crossover_max_gradient_degree=25.72682242872742,
    crossover_gradient_signal_weight=0.2399,
    crossover_weight_impact=0.33062400559960325,
    zero_line_crossover_weight=0.9987157290164548,
    zero_line_pullback_lookback=2,
    zero_line_pullback_tolerance_percent=0.3276036034958676,
    zero_line_pullback_weight=1.766904365264866e-08
)

def main():
    setup_logger(
        'oracle.link',
        DEBUG,
        './logs/paperTrade.jsonl',
        log_in_json=False,
        stream_in_color=True,
        extra_log_args=["open_timestamp"],
    )

    pt = PaperTrader(
        symbol = "DOGEUSDT", #input('Enter symbol: '),
        interval = "1m", #input('Enter interval: '),
        limit = 100, #int(input('Enter limit: ')),
        risk_per_position = 0.01, #float(input('Enter risk per position (% 0-1): ')),
        seconds_to_sleep= 5, #int(input('Enter sleep interval: ')),
        initial_balance = 10000, #float(input('Enter initial balance: ')),
        leverage = 1, #float(input('Enter leverage: ')), #NOT IMPLEMENTED
        stop_loss= 2, #float(input('Enter stop loss (% 0-1): ')),
        take_profit= 4, # float(input('Enter take profit (% 0-1): ')),
        buy_conf_threshold= 0.8, #float(input('Enter buy confidence threshold (0 to 1): ')),
        sell_conf_threshold= 0.8, #float(input('Enter sell confidence threshold (-1 to 0): ')),
        strat = strat,
        save_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/paperTradeData'),
    )
    pt.run()

if __name__ == '__main__':
    main()