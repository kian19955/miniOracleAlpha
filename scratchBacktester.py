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

    leverage = 1

    def init(self):
        if self.eval_func is None:
            raise ValueError("You must set 'eval_func' to a callable that returns a confidence signal.")

        self.tp_level: Optional[float] = None
        self.sl_level: Optional[float] = None

        self.position_entered = False

    def create_sl(self, position_long: bool):
        if self.stop_loss is not None:
            if position_long:
                limit = self.data.Close[-1] * (1 - self.stop_loss)
            else:
                limit = self.data.Close[-1] * (1 + self.stop_loss)

            self.sl_level = limit
            return limit

    def create_tp(self, position_long: bool):
        if self.stop_loss is not None:
            if position_long:
                limit = self.data.Close[-1] * (1 + self.take_profit)
            else:
                limit = self.data.Close[-1] * (1 - self.take_profit)

            self.tp_level = limit
            return limit

    def next(self):
        conf = self.eval_func(self.data.df)

        # If confidence indicates a 'sell' signal (i.e. want to be short)
        if conf <= self.sell_limit:
            if self.trade_short and not self.position or self.position.is_long:
                self.sell(sl=self.create_sl(False), tp=self.create_tp(False))
            elif self.position.is_long:
                self.position.close()

        # If confidence indicates a 'buy' signal (i.e. want to be long)
        elif conf >= self.buy_limit:
            if not self.position or self.position.is_short:
                self.buy(sl=self.create_sl(True), tp=self.create_tp(True))
            elif self.position.is_short:
                self.position.close()

    def on_trade(self, trade):
        if trade.is_closed:
            if self.tp_level is not None and trade.exit_price >= self.tp_level:
                print("Trade closed due to take profit.")

            elif self.sl_level is not None and trade.exit_price <= self.sl_level:
                print("Trade closed due to stop loss.")

            self.tp_level, self.sl_level = None, None


def backtest(
    eval_func,
    ticker,
    days, interval,
    commission = 0.00075,
    sell_limit = -0.75, buy_limit = 0.75,
    trade_long = True, trade_short = True,
    stop_loss = None, take_profit = None,
    margin = 1,
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
        cash=10000,
        margin=margin,
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
        stop_loss=0.001,
        take_profit=0.001,
        micro_factor=1000000
    )

    print(stats)
    bt.plot(open_browser=False)