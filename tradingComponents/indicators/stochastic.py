from pandas import DataFrame, Series
from pandas_ta import sma

from tradingComponents.indicators.crossoverUtil import check_crossover

class Stochastic:
    def __init__(self, lookback_period: int = 14, smoothing_period: int = 3, crossover_return_strength: bool = False,
                 crossover_max_gradient_degree: float = 90, crossover_gradient_signal_weight: float = 1, crossover_weight_impact: float = 1,
                 crossover_weight: float = 1, stochastic_weight: float = 1):
        self.lookback_period = lookback_period
        self.smoothing_period = smoothing_period
        self.crossover_return_strength = crossover_return_strength
        self.crossover_max_gradient_degree = crossover_max_gradient_degree
        self.crossover_gradient_signal_weight = crossover_gradient_signal_weight
        self.crossover_weight_impact = crossover_weight_impact
        self.crossover_weight = crossover_weight
        self.stochastic_weight = stochastic_weight

    def evaluate(self, df: DataFrame) -> float:
        valid_range: float = self.lookback_period + 1
        if len(df) < valid_range:
            return 0

        valid_df: Series = df.iloc[-valid_range:]

        lowest_low = valid_df["Low"].min()
        highest_high = valid_df["High"].max()

        k = ((valid_df["Close"] - lowest_low) / (highest_high - lowest_low))

        d = sma(k, self.smoothing_period)

        crossover: float = check_crossover(
            k.iloc[-1],
            d.iloc[-1],
            k.iloc[-2],
            d.iloc[-2],
            return_strength=self.crossover_return_strength,
            max_gradient_degree=self.crossover_max_gradient_degree,
            gradient_signal_weight=self.crossover_gradient_signal_weight,
            weight_impact=self.crossover_weight_impact
        )

        k_confidence: float = d.iloc[-1] * 2 - 1

        weight_sum: float = self.crossover_weight + self.stochastic_weight
        confidences: float = crossover * self.crossover_weight + k_confidence * self.stochastic_weight

        confidence: float = confidences / weight_sum

        return confidence