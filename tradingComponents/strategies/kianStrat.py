from typing import Optional

from pandas import DataFrame

from tradingComponents.Dow import detect_dow_trend
from tradingComponents.Dow.utils.dowEnums import Trend


class KianStrat:
    def __init__(self, check_trend: bool = True):
        self.check_trend = check_trend

    def evaluate(
            self, df: DataFrame,
    ) -> float:
        """
        ...

        The df needs to be the same as the one used to detect the peaks and valleys

        :param df: DataFrame of klines

        :return: -1 (Sell), 0 (Hold), 1 (Buy) Or a float indicating the probability of a successful order(-1 - 1)
        """
        trend_info, peaks, valleys = detect_dow_trend(df)

        if peaks is None or valleys is None:
            return 0

        peak_and_low_candle_distance_delta = abs(peaks[-1] - valleys[-1]) # <-- The difference between the last peak and the last valley ###KIAN

        # Buy
        if (peaks[-1] < valleys[-1] and
            (not self.check_trend or trend_info['trend'] == Trend.UPTREND) and
            df.get('Close').iloc[-1] > df.iloc[peaks[-1]]['Close']): # <-- Under what price it should buy ###KIAN
            return 1

        # Sell
        elif (valleys[-1] < peaks[-1] and
              (not self.check_trend or trend_info['trend'] == Trend.DOWNTREND) and
              df.get('Close').iloc[-1] < df.iloc[valleys[-1]]['Close']): # <-- Under what price it should sell ###KIAN
            return -1

        return 0

