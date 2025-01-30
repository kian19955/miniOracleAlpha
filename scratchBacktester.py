from collections.abc import Callable
from typing import Optional
import backtrader as bt
import pandas as pd
from api.binanceApi import fetch_klines
from constants import bt_data_dir_path


import backtrader as bt
import pandas as pd
from typing import Callable

class OracleStrategy(bt.Strategy):
    params: tuple[str, any] = (
        ('eval_func', None),
        ('sell_limit', -0.75),
        ('buy_limit', 0.75),
        ('trade_long', True),
        ('trade_short', True),
        ('leverage', 1),
        ('maker_fee', 0.00075),
        ('taker_fee', 0.00075),
    )

    def __init__(self):
        self.confidence = 0.0
        self.order = None
        self.data_buffer = []

        # Initialize fee structure
        self.broker.setcommission(
            commission=self.p.maker_fee,
            leverage=self.p.leverage
        )

    def log(self, message):
        print(f"{self.datetime.datetime(0)} - {message}")

    def next(self):
        # Store historical data
        self.data_buffer.append({
            'open': self.data.open[0],
            'high': self.data.high[0],
            'low': self.data.low[0],
            'close': self.data.close[0],
            'volume': self.data.volume[0],
            'datetime': self.data.datetime.datetime(0)
        })

        # Evaluate confidence
        self.confidence = self.p.eval_func(pd.DataFrame(self.data_buffer))

        # Check for open orders
        if self.order:
            return

        # Trading logic
        if self.confidence <= self.p.sell_limit:
            self._execute_sell_sequence()
        elif self.confidence >= self.p.buy_limit:
            self._execute_buy_sequence()

    def _execute_buy_sequence(self):
        if self.p.trade_short and self.position.size < 0:
            self.close()
            self.log(f"Closing SHORT at {self.data.close[0]}")

        if self.p.trade_long and self.position.size == 0:  # Prevent multiple buys
            size = self.broker.getcash() * self.p.leverage / self.data.close[0]
            self.buy(size=size)
            self.log(f"Opening LONG at {self.data.close[0]}")

    def _execute_sell_sequence(self):
        if self.p.trade_long and self.position.size > 0:
            self.close()
            self.log(f"Closing LONG at {self.data.close[0]}")

        if self.p.trade_short and self.position.size == 0:  # Prevent multiple shorts
            size = self.broker.getcash() * self.p.leverage / self.data.close[0]
            self.sell(size=size)
            self.log(f"Opening SHORT at {self.data.close[0]}")


def backtest(
        eval_func: Callable,
        ticker: str,
        days: int = 14,
        interval: str = "1m",
        maker_fee: float = 0.00075,
        taker_fee: float = 0.00075,
        sell_limit: float = -0.75,
        buy_limit: float = 0.75,
        trade_long: bool = True,
        trade_short: bool = True,
        leverage: int = 1,
        use_csv: bool = True
):
    # Fetch/prepare data
    df = fetch_klines(ticker, interval, days=days, use_csv=use_csv)

    # Create Backtrader data feed
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,
        open=0,
        high=1,
        low=2,
        close=3,
        volume=4
    )

    # Initialize Cerebro engine
    cerebro = bt.Cerebro()
    cerebro.adddata(data, name=ticker)

    # Add strategy with parameters
    cerebro.addstrategy(OracleStrategy,
                        eval_func=eval_func,
                        sell_limit=sell_limit,
                        buy_limit=buy_limit,
                        trade_long=trade_long,
                        trade_short=trade_short,
                        leverage=leverage,
                        maker_fee=maker_fee,
                        taker_fee=taker_fee
                        )

    # Set initial capital
    cerebro.broker.setcash(100.0)

    # ✅ **Add built-in trade tracking (Option 2)**
    cerebro.addobserver(bt.observers.Trades)

    # ✅ **Add Buy/Sell markers (Option 3)**
    cerebro.addobserver(bt.observers.BuySell, barplot=True)

    # Run backtest
    results = cerebro.run()

    # Plot the results
    cerebro.plot(style='candlestick')

    return df, results[0]


if __name__ == '__main__':
    from tradingComponents.indicators import RelativeStrengthIndex
    tc = RelativeStrengthIndex(

    )

    ticker = "SOLUSDT"
    days = 7
    interval = "1m"

    print(f"Running backtest for {ticker} over {days} days with {interval} interval...")

    # Run backtest with placeholder evaluation function
    df, strategy = backtest(
        eval_func=tc.evaluate,
        ticker=ticker,
        days=days,
        interval=interval,
        use_csv=True
    )

    # Print final results
    print("\nBacktest completed!")
    print(f"Final Portfolio Value: ${strategy.broker.getvalue():.2f}")
    print(f"Final Cash: ${strategy.broker.getcash():.2f}")
    print(f"Trade history saved to: {bt_data_dir_path}/{ticker}_{days}_{interval}_orders.csv")