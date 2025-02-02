from typing import Optional

from backtesting import Backtest, Strategy
import pandas as pd

from api.binanceApi import fetch_klines


class Backtester(Strategy):
    eval_func = None

    sell_limit = -0.75
    buy_limit = 0.75

    trade_long = True
    trade_short = True

    take_profit = None
    stop_loss = None

    def init(self):
        if self.eval_func is None:
            raise ValueError("You must set 'eval_func' to a callable that returns a confidence signal.")

        self.position_closed: bool = False

    def create_sl(self, position_long: bool):
        if self.stop_loss is not None:
            if position_long:
                stop = self.data.Close[-1] * (1 - self.stop_loss)
            else:
                stop = self.data.Close[-1] * (1 + self.stop_loss)

            return stop

    def create_tp(self, position_long: bool):
        if self.stop_loss is not None:
            if position_long:
                limit = self.data.Close[-1] * (1 + self.take_profit)
            else:
                limit = self.data.Close[-1] * (1 - self.take_profit)

            return limit

    def next(self):
        conf = self.eval_func(self.data.df)

        if not self.position and not self.position_closed:
            self.on_close(True)

        elif not self.position and self.position_closed:
            self.on_close(True)
            self.position_closed = False

        # If confidence indicates a 'sell' signal (i.e. want to be short)
        if conf <= self.sell_limit:
            if self.trade_short and not self.position or self.position.is_long:
                self.sell(sl=self.create_sl(False), tp=self.create_tp(False))
            elif self.position.is_long:
                self.position_closed = True
                self.position.close()

        # If confidence indicates a 'buy' signal (i.e. want to be long)
        elif conf >= self.buy_limit:
            if not self.position or self.position.is_short:
                self.buy(sl=self.create_sl(True), tp=self.create_tp(True))
            elif self.position.is_short:
                self.position_closed = True
                self.position.close()

    def on_close(self, user_closed: bool = False):
        ...

def backtest(
    eval_func,
    ticker,
    days, interval,
    commission = 0.00075,
    sell_limit = -0.75, buy_limit = 0.75,
    trade_long = True, trade_short = True,
    stop_loss = None, take_profit = None,
    leverage = 1,
    micro_factor: Optional[int] = None,
    use_csv = True,
) -> tuple[pd.DataFrame, Backtest]:
    df = fetch_klines(ticker, interval, days=days, use_csv=use_csv)

    if micro_factor is not None:
        df = (df / micro_factor).assign(Volume=df.Volume * micro_factor)

    # Create the backtest object with your strategy
    bt: Backtest = Backtest(
        df,
        Backtester,
        commission=commission,
        cash=100000000,
        margin=leverage,
    )

    bt._strategy.eval_func = eval_func

    bt._strategy.sell_limit = sell_limit
    bt._strategy.buy_limit = buy_limit

    bt._strategy.trade_long = trade_long
    bt._strategy.trade_short = trade_short

    bt._strategy.take_profit = take_profit
    bt._strategy.stop_loss = stop_loss

    # Run the backtest
    stats = bt.run()
    return stats, bt


if __name__ == "__main__":
    from tradingComponents.indicators import RelativeStrengthIndex
    tc = RelativeStrengthIndex(period=14, lower_band=30, upper_band=70)
    stats, bt = backtest(
        tc.evaluate,
        ticker="BTCUSDT",
        days=1,
        interval="1m",
        sell_limit=-0.75,
        buy_limit=0.75,
        stop_loss=None,
        take_profit=None,
        micro_factor=None
    )

    print(stats)
    bt.plot(open_browser=False)