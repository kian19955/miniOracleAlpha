from pandas import DataFrame, Series
from numpy import nan, where
import mplfinance as mpf

from enum import Enum

class CandleTypes(Enum):
    CANDLE = "candle"
    LINE = "line"
    OHLCV = "ohlc"
    RENKO = "renko"
    PNF = "pnf"

def plot_data(
        plot_title: str,
        his_df: DataFrame,
        bt_df: DataFrame,
        sell_limit: float,
        buy_limit: float,
        display_volume: bool,
        plot_liquidity: bool,
        plot_orders: bool,
        plot_limits: bool,
        plot_conf: bool
):
    # Buy and sell orders
    buy_orders_series: Series = Series(
        where(bt_df['type'] == 'buy', bt_df['price'], nan),
        index=his_df.index
    )

    sell_orders_series: Series = Series(
        where(bt_df['type'] == 'sell', bt_df['price'], nan),
        index=his_df.index
    )

    add_plots = []

    if plot_liquidity:
        add_plots.append(mpf.make_addplot(bt_df['liquidity'], type="line", color="aqua", label="Liquidity"))

    if plot_orders:
        if not buy_orders_series.isna().all():
            add_plots.append(
                mpf.make_addplot(buy_orders_series, type="scatter", marker="^", color="green", markersize=100,
                                 label="Buy"))
        if not sell_orders_series.isna().all():
            add_plots.append(
                mpf.make_addplot(sell_orders_series, type="scatter", marker="v", color="red", markersize=100,
                                 label="Sell"))

    # Limits
    if plot_limits:
        if sell_limit is not None:
            sell_limit_series: Series = Series(sell_limit, index=his_df.index)
            add_plots.append(mpf.make_addplot(sell_limit_series, type="line", color="red", label="Sell Limit"))
        if buy_limit is not None:
            buy_limit_series: Series = Series(buy_limit, index=his_df.index)
            add_plots.append(mpf.make_addplot(buy_limit_series, type="line", color="green", label="Buy Limit"))

    # Confidence
    if plot_conf:
        add_plots.append(mpf.make_addplot(bt_df['confidence'], type="line", color="blue", label="Confidence"))

    mpf.plot(
        his_df,
        type=CandleTypes.CANDLE.value,
        style="binance",
        title=plot_title,
        volume=display_volume,
        show_nontrading=True,
        addplot=add_plots
    )