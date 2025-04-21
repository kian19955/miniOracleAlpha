from pandas import DataFrame
from pandas_ta import sma as create_sma

### Return stop based on shadow size

class ShadowsTrendingTouch:
    def __init__(self, sma_period: int = 7, shadow_to_body_ratio: float = 1.25,
                 shadow_padding_price: int = 2, opposite_shadow_to_body_ratio: float = 0.25):
        self.sma_period = sma_period
        self.shadow_to_body_ratio = shadow_to_body_ratio
        self.shadow_padding_price = shadow_padding_price
        self.opposite_shadow_to_body_ratio = opposite_shadow_to_body_ratio

    def evaluate(self, df: DataFrame) -> float:
        valid_df_range: int = self.sma_period + 1
        if len(df) < valid_df_range:
            return 0

        self_df = df.copy().iloc[-valid_df_range:]
        last_candle = self_df.iloc[-1]
        sma = create_sma(close=self_df.Close, length=self.sma_period)

        # Candle Body doesn't touch SMA
        if last_candle.Open < sma.iloc[-1] < last_candle.Close:
            return 0

        candle_above_sma = last_candle.Close > sma.iloc[-1]
        bullish_candle = last_candle.Open < last_candle.Close

        # Bullish candle and above sma OR Bearish candle and below sma
        if bullish_candle != candle_above_sma:
            return 0

        # Find Shadow Touching Size
        if bullish_candle:
            shadows_touch_size = last_candle.Open - last_candle.Low
            opposite_shadow_size = last_candle.High - last_candle.Close
        else:
            shadows_touch_size = last_candle.High - last_candle.Close
            opposite_shadow_size = last_candle.Open - last_candle.Low

        # Shadow to Body Ratio is big enough
        body_size = abs(last_candle.Open - last_candle.Close)
        if shadows_touch_size / body_size < self.shadow_to_body_ratio: # Green Close to High, Red Close to Low
            return 0

        # Opposite shadow small enough
        if opposite_shadow_size / body_size > self.opposite_shadow_to_body_ratio:
            return 0

        # Check candles touching
        if bullish_candle:
            if last_candle.Low - self.shadow_padding_price <= sma.iloc[-1]:
                return 1
        else:
            if last_candle.High + self.shadow_padding_price >= sma.iloc[-1]:
                return -1

        return 0
