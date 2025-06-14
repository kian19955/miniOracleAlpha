import os
from logging import DEBUG
import random
from custom_logger import setup_logger
from paperTrading import PaperTrader

from tradingComponents.strategies.kianStrat import KianStrat

strat = KianStrat(
    check_trend=True
)

class TestStrat:
    def __init__(self):
        pass

    def evaluate(self, *args, **kwargs):
        return random.choice([1, -1])

def main():
    setup_logger(
        'oracle.analysis',
        DEBUG,
        './logs/paperTrade.jsonl',
        log_in_json=False,
        stream_in_color=True,
        extra_log_args=[],
    )

    pt = PaperTrader(
        symbol = "DOGEUSDT", #input('Enter symbol: '),
        interval = "1m", #input('Enter interval: '),
        lookback= 100, #int(input('Enter limit: ')),

        max_positions = 1, #int(input('Enter max positions: ')),
        seconds_to_sleep=5,  # int(input('Enter sleep interval: ')),
        block_reentry_until_signal_reset=True,

        initial_balance=10000,  # float(input('Enter initial balance: ')),
        risk_per_trade= 0.01, #float(input('Enter risk per position (% 0-1): ')),
        leverage = 1, #float(input('Enter leverage: ')), #NOT IMPLEMENTED

        stop_loss_pct = 2, #float(input('Enter stop loss (% 0-1): ')),
        take_profit_pct = 4, # float(input('Enter take profit (% 0-1): ')),

        buy_conf_threshold= 0.8, #float(input('Enter buy confidence threshold (0 to 1): ')),
        sell_conf_threshold= -0.8, #float(input('Enter sell confidence threshold (-1 to 0): ')),

        strat = strat,
        save_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'),
    )
    pt.run(
        start_on_new_candle=False,
    )

if __name__ == '__main__':
    main()