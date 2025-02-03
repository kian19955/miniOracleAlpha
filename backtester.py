from typing import Optional

from backtesting import Backtest, Strategy
import pandas as pd
from backtesting.backtesting import Trade

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

        self.position_opened: bool = False
        self.confs = self.I(self.compute_confs, self.data.df)

    def compute_confs(self, df):
        """
        Compute a signal value for each candle by iteratively calling eval_func on
        the data from the start until the current candle.
        """
        signals = []
        for i in range(1, len(df) + 1):
            # Slice the dataframe up to and including the current candle
            sub_df = df.iloc[:i]
            # Call the evaluation function on the sub-dataframe
            signal = self.eval_func(sub_df)
            signals.append(signal)

        return signals

    def create_sl(self, position_long: bool):
        if self.stop_loss is None:
            return None
        multiplier = 1 - self.stop_loss if position_long else 1 + self.stop_loss
        return self.data.Close[-1] * multiplier

    def create_tp(self, position_long: bool):
        if self.take_profit is None:
            return None
        multiplier = 1 + self.take_profit if position_long else 1 - self.take_profit
        return self.data.Close[-1] * multiplier

    def next(self):
        conf = self.confs[-1]

        if self.position_opened and not self.position:
            self.on_close()

        if conf <= self.sell_limit:
            # Sell condition
            if self.trade_short and (not self.position or self.position.is_long):
                self.sell(sl=self.create_sl(False), tp=self.create_tp(False))
                self.position_opened = True

            # Close long position only if not opening short
            elif not self.trade_short and self.position.is_long:
                self.position.close()

        elif conf >= self.buy_limit:
            # Buy condition
            if self.trade_long and (not self.position or self.position.is_short):
                self.buy(sl=self.create_sl(True), tp=self.create_tp(True))
                self.position_opened = True

            # Close short position only if not opening long
            elif not self.trade_long and self.position.is_short:
                self.position.close()


    def on_close(self):
        if not self.trades:
            return

        latest_trade: Trade = self.trades[-1]

        if latest_trade.exit_price == latest_trade.sl:
            print("SL triggered")

        elif latest_trade.exit_price == latest_trade.tp:
            print("TP triggered")


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
        cash=10000,
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
    tc = RelativeStrengthIndex(period=3, lower_band=28.400000000000002, upper_band=77.4)
    stats, bt = backtest(
        tc.evaluate,
        ticker="DOGEUSDT",
        days=7,
        interval="5m",
        sell_limit=-0.75,
        buy_limit=0.75,
        stop_loss=None,
        take_profit=None,
        trade_long=False,
        micro_factor=1,
        leverage=1
    )

    print(stats._trades)
    print(stats)
    bt.plot(open_browser=False)