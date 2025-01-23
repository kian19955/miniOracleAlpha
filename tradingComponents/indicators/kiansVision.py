from typing import Optional, Callable
from enum import Enum

from pandas import DataFrame
from numpy import ndarray
from sklearn.cluster import DBSCAN


class FilterMethod(Enum):
    ITERATIVE_MEDIAN = "iterative_median"  # User-defined iterations
    PERCENTILE = "percentile"  # Statistically adaptive
    CLUSTERING = "clustering"  # Advanced (DBSCAN)

class KiansVision:
    def __init__(
            self,
            lookback_period: int = 50,
            n_highest_highs: int = 3,
            n_lowest_lows: int = 3,
            percentage_of_highest_highs: Optional[float] = None,
            percentage_of_lowest_lows: Optional[float] = None,
            filter_method: FilterMethod = FilterMethod.ITERATIVE_MEDIAN,
            filter_setting: float = 2.5,
            clustering_eps: Optional[float] = None,
            filter_iterations: Optional[int] = 2
    ):
        """
        This indicator uses the occurrences of prices and their trading volume over the lookback_period, to determine where the price will likely shift

        NOTE: percentage_of_highest_highs and percentage_of_lowest_lows will always be prioritized over n_highest_highs and n_lowest_lows

        :param lookback_period: The lookback period for the indicator
        :param n_highest_highs: The number of highest highs which will indicate the trend
        :param n_lowest_lows: The number of lowest lows which will indicate the trend
        :param percentage_of_highest_highs: The percentage of all prices which will be considered the highest highs and used to indicate the trend
        :param percentage_of_lowest_lows: The percentage of all prices which will be considered the lowest lows and used to indicate the trend
        :param filter_method: The method used to filter the indicator, Options are ITERATIVE_MEDIAN, PERCENTILE, CLUSTERING
        :param filter_setting:
        - ITERATIVE_MEDIAN: A multiplier applied to the average volume to determine the maximum valid volume threshold. Volume levels exceeding this threshold are considered noise and ignored
        - PERCENTILE: A percentile applied to the volume, to filter out the highest volumes. (Range 0<n<=1)
        - CLUSTERING: Uses DBSCAN and filters out the highest volumes. This value will be used to determine the min_points that need to be in eps range for the point to be considered a main point
        :param clustering_eps: The epsilon value used for DBSCAN. Indicates the range of points that are considered neighbors. The points are plotted in volume level.
        :param filter_iterations: The number of times the indicator will be filtered. If None it filters indefinitely until nothing can get filtered anymore, caps at 100 iterations
        """
        self.lookback_period = lookback_period
        self.n_highest_highs = n_highest_highs
        self.n_lowest_lows = n_lowest_lows
        self.percentage_of_highest_highs = percentage_of_highest_highs
        self.percentage_of_lowest_lows = percentage_of_lowest_lows
        self.filter_method = filter_method
        self.filter_setting = filter_setting
        self.clustering_eps = clustering_eps
        self.filter_iterations = min(filter_iterations, 100)

    def evaluate(self, df: DataFrame):
        valid_df_range: int = self.lookback_period + 1
        if len(df) < valid_df_range:
            return 0

        df: DataFrame = df.iloc[-valid_df_range:]
        df = self.filter(df)

        return df


    def filter(self, df: DataFrame) -> DataFrame:
        filter_methode: Callable[[DataFrame], DataFrame]

        match self.filter_method:
            case FilterMethod.ITERATIVE_MEDIAN:
                filter_methode = self.iterative_median_filter
            case FilterMethod.PERCENTILE:
                filter_methode = self.percentile_filter
            case FilterMethod.CLUSTERING:
                filter_methode = self.clustering_filter

        original_df_length: int = len(df)
        for _ in range(self.filter_iterations):
            df = filter_methode(df)

            if len(df) == original_df_length:
                break

            original_df_length = len(df)

        return df

    def iterative_median_filter(self, df: DataFrame) -> DataFrame:
        median: float = df["Volume"].median()
        threshold: float = median * self.filter_setting
        filtered_df = df[df["Volume"] <= threshold]

        return filtered_df

    def percentile_filter(self, df: DataFrame) -> DataFrame:
        threshold: float = df["Volume"].quantile(self.filter_setting)
        filtered_df = df[df["Volume"] <= threshold]

        return filtered_df

    def clustering_filter(self, df: DataFrame) -> DataFrame:
        volumes: ndarray = df["Volume"].values.reshape(-1, 1)
        clustering: object = DBSCAN(eps=self.clustering_eps, min_samples=self.filter_setting).fit(volumes)
        filtered_df = df[clustering.labels_ == 1]

        return filtered_df



if __name__ == '__main__':
    from api.binanceApi import fetch_klines
    df = fetch_klines("BTCUSDT", "1m", minutes=1000)
    import matplotlib.pyplot as plt

    def plot_price_occurrences(df: DataFrame, title: str):
        # Count occurrences of each price level
        price_occurrences = df["Close"].value_counts().sort_index()

        # Plot bar graph
        plt.figure(figsize=(12, 6))
        plt.bar(price_occurrences.index, price_occurrences.values, width=0.1, color='blue')
        plt.xlabel("Price")
        plt.ylabel("Occurrences")
        plt.title(title)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.show()


    plot_price_occurrences(df, "Price Occurrences")

    kv = KiansVision(
        lookback_period=1000,
        filter_method=FilterMethod.CLUSTERING,
        filter_setting=3,
        clustering_eps=0.1
    )

    df = kv.evaluate(df)

    plot_price_occurrences(df, "Filtered Price Occurrences")
