import logging

from pandas import DataFrame, Series
from pandas_ta import rsi

class RelativeStrengthIndex():
    """
    Implements the Relative Strength Index (RSI) trading strategy.

    The RSI is a momentum oscillator that measures the speed and change of price movements.
    It oscillates between 0 and 100 and is typically used to identify overbought or oversold conditions.
    This strategy evaluates whether the market conditions are ripe for buying or selling based on RSI limits.

    Methods
    -------
    determine_trade_signal(rsi_value: float, lower_band: int = 30, upper_band: int = 70) -> int | None
        Determines whether the signal is to buy (1), sell (0), or hold (None) based on the RSI value and bands.

    evaluate(df: DataFrame, period: int = 14, lower_band: int = 30, upper_band: int = 70) -> int | None
        Evaluates the RSI for the provided DataFrame and returns a buy, sell, or hold signal.

    backtestData(df: DataFrame, period: int = 14, lower_band: int = 30, upper_band: int = 70, partition_frequency: int = 31) -> float
        Backtests the RSI strategy on historical data and calculates the Return on Investment (ROI).
    """
    GA_GENOME_SETTINGS: dict[str, dict[type, dict[str | type, any]]] = {
        'period': {
            int: {
                'start': 1,
                'stop': 20,
                'step': 1
            }
        },
        'lower_band': {
            float: {
                'start': 0,
                'stop': 50,
                'step': 0.1
            }
        },
        'upper_band': {
            float: {
                'start': 50,
                'stop': 100,
                'step': 0.1
            }
        }
    }

    def __init__(self, period: int = 14, lower_band: float = 30, upper_band: float = 70, rsi_as_signal: bool = False):
        """
        Initializes the Relative Strength Index (RSI) trading strategy.

        :key period: The period to use for RSI calculation (default is 14).
        :key lower_band: The lower RSI limit for a buy signal (default is 30).
        :key upper_band: The upper RSI limit for a sell signal (default is 70).
        :key dynamic_return: Whether to use dynamic returns (default is False).
        """
        self.period = period
        self.lower_band = lower_band
        self.upper_band = upper_band
        self.rsi_as_signal = rsi_as_signal

    def evaluate(self, df: DataFrame) -> float:
        """
        Determines whether the signal is to buy, sell, or hold based on the RSI value.

        This method uses predefined RSI bands to classify market conditions into buy, sell, or hold signals:
        - Buy when RSI is below the lower band (default 30).
        - Sell when RSI is above the upper band (default 70).
        - Hold if RSI is between the lower and upper bands.

        :return: 1 for Buy, -1 for Sell, or 0 for Hold.
        """
        valid_df_range = self.period + 1
        if len(df) < valid_df_range:
            return 0

        self_df: DataFrame = df.iloc[-valid_df_range:]
        rsi_series: Series = rsi(close=self_df.Close, length=self.period)

        rsi_value: float = rsi_series.iloc[-1]

        if self.rsi_as_signal:
            return ((50 - rsi_value) * 2) / 100

        if rsi_value < self.lower_band:
            return 1
        elif rsi_value > self.upper_band:
            return -1
        else:
            return 0
