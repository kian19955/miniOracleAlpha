from typing import Optional

from pandas import DataFrame

from tradingComponents.Dow import detect_dow_trend
from tradingComponents.Dow.utils.dowEnums import Trend
from paperTrading.models import OrderRequest, Portfolio
from paperTrading.enums import PositionDirection, OrderAction


class KianStrat:
    def __init__(self, check_trend: bool = True, risk_to_reward: float = 2, stop_loss_limit: float = 0.003):
        self.check_trend = check_trend
        self.risk_to_reward = risk_to_reward
        self.stop_loss_limit = stop_loss_limit

    def evaluate(
            self, df: DataFrame,
            trend_info: Optional[dict[str, any]] = None,
            peaks: Optional[list[int]] = None,
            valleys: Optional[list[int]] = None,
            portfolio: Portfolio = None
    ) -> float | OrderRequest:
        """
        ...

        The df needs to be the same as the one used to detect the peaks and valleys

        :param df: DataFrame of klines
        :param trend_info: Dictionary of trend info
        :param peaks: Array of num of index candle for each peak
        :param valleys: Array of num of index candle for each valley
        :param portfolio: Portfolio
        :return: -1 (Sell), 0 (Hold), 1 (Buy) Or a float indicating the probability of a successful order(-1 - 1)
        """
        if peaks is None or valleys is None:
            trend_info, peaks, valleys = detect_dow_trend(df.iloc[:-1])

        if self.check_trend and trend_info is None:
            return 0

        latest_peak_price: float = df.iloc[peaks[-1]]['Close']
        latest_valley_price: float = df.iloc[valleys[-1]]['Close']

        latest_price: float = df.iloc[-1]['Close']
        peak_and_low_candle_distance_delta = abs(peaks[-1] - valleys[-1])

        # Buy
        if (peaks[-1] < valleys[-1] and
                (not self.check_trend or trend_info['trend'] == Trend.UPTREND) and
                latest_price > latest_peak_price):
            # Send only if stop loss is 0.3% or higher
            if abs(latest_valley_price-latest_price)/latest_price < self.stop_loss_limit:
                return 0


            return OrderRequest(
                confidence=1,
                direction=PositionDirection.LONG,
                action=OrderAction.OPEN,
                stop_loss=latest_valley_price,
                take_profit=latest_price + self.risk_to_reward * (latest_price - latest_valley_price) # (latest_peak_price - latest_valley_price),
            )

        # Sell
        elif (valleys[-1] < peaks[-1] and
              (not self.check_trend or trend_info['trend'] == Trend.DOWNTREND) and
              latest_price < latest_valley_price):

            # Send only if stop loss is 0.3% or higher
            if abs(latest_peak_price-latest_price)/latest_price < self.stop_loss_limit:
                return 0

            return OrderRequest(
                confidence=-1,
                direction=PositionDirection.SHORT,
                action=OrderAction.OPEN,
                stop_loss=latest_peak_price,
                take_profit=latest_price - self.risk_to_reward * (latest_peak_price - latest_price) # (latest_peak_price - latest_valley_price),
            )

        return 0
