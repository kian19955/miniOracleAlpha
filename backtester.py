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

        if self.stop_loss == 0:
            self.stop_loss = None

        if self.take_profit == 0:
            self.take_profit = None

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
        if position_long:
            return self.data.Close[-1] * (1 - self.stop_loss)
        else:
            return self.data.Close[-1] * (1 + self.stop_loss)

    def create_tp(self, position_long: bool):
        if self.take_profit is None:
            return None
        if position_long:
            return self.data.Close[-1] * (1 + self.take_profit)
        else:
            return self.data.Close[-1] * (1 - self.take_profit)

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
) -> tuple[pd.Series, Backtest]:
    df = fetch_klines(ticker, interval, days=days, use_csv=use_csv)

    if micro_factor is not None:
        df = (df / micro_factor).assign(Volume=df.Volume * micro_factor)

    # Create the backtest object with your strategy
    bt: Backtest = Backtest(
        df,
        Backtester,
        commission=commission,
        cash=10000,
        margin=1/leverage,
    )

    # Run the backtest
    stats = bt.run(
        eval_func=eval_func,
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        trade_long=trade_long,
        trade_short=trade_short,
        take_profit=take_profit,
        stop_loss=stop_loss
    )
    return stats, bt


if __name__ == "__main__":
    from tradingComponents.indicators import RelativeStrengthIndex, MovingAverageConvergenceDivergence

    settings = {'fast_period': 42, 'slow_period': 90, 'signal_line_period': 24, 'momentum_max_lookback': 51,
                'momentum_signal_weight': 0.5578000000000001, 'crossover_return_weight': True,
                'crossover_max_gradient_degree': 88.03937584556466, 'crossover_gradient_signal_weight': 0.8212,
                'crossover_weight_impact': 0.1265, 'zero_line_crossover_weight': 0.998639817622752,
                'zero_line_pullback_lookback': 19,
                'zero_line_pullback_tolerance_percent': 0.5487446218136476,
                'zero_line_pullback_weight': 0.41714182779059517,
                'return_pullback_strength': True, 'magnitude_weight': 0.8083685289854661,
                'rate_of_change_weight': 0.9985617455723734,
                'weight_impact': 0.4497}
    # settings = {'period': 17, 'lower_band': 3.550917741204702, 'upper_band': 73.09752054858266}

    tc = MovingAverageConvergenceDivergence(
        **settings
    )

    stats, bt = backtest(
        tc.evaluate,
        ticker="DOGEUSDT",
        days=93,
        interval="1h",
        sell_limit=-0.75,
        buy_limit=0.75,
        stop_loss=None,
        take_profit=None,
        trade_long=True,
        micro_factor=None,
        leverage=1
    )

    print(stats._trades)
    print(stats)
    bt.plot()
