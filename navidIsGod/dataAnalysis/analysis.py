from enum import Enum
from typing import Optional

import mplfinance as mpf
import pandas as pd
from numpy import nan, where
from pandas import DataFrame, read_csv, Series

from navidIsGod.constants import market_his_dir_path, bt_data_dir_path


class CandleTypes(Enum):
    CANDLE = "candle"
    LINE = "line"
    OHLCV = "ohlc"
    RENKO = "renko"
    PNF = "pnf"


def analyze(
        target_filename: str,
        his_df: Optional[DataFrame] = None,
        bt_df: Optional[DataFrame] = None,
        sell_limit: Optional[float] = None,
        buy_limit: Optional[float] = None,
        display_volume: bool = True,
        plot_liquidity: bool = True,
        plot_orders: bool = True,
        plot_limits: bool = True,
        plot_conf: bool = True
):
    # Load data
    if his_df is None:
        his_df: DataFrame = read_csv(f"{market_his_dir_path}/{target_filename}")
        his_df.set_index("timestamp", inplace=True)
        his_df.index = pd.to_datetime(his_df.index)

    if bt_df is None:
        bt_df: DataFrame = read_csv(f"{bt_data_dir_path}/{target_filename}")
        bt_df.set_index("timestamp", inplace=True)
        bt_df.index = pd.to_datetime(bt_df.index)



    ## Prepare data for plotting
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
        add_plots.append(mpf.make_addplot(buy_orders_series, type="scatter", marker="^", color="green", markersize=100, label="Buy"))
        add_plots.append(mpf.make_addplot(sell_orders_series, type="scatter", marker="v", color="red", markersize=100, label="Sell"))

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
        title=target_filename,
        volume=display_volume,
        show_nontrading=True,
        addplot=add_plots
    )
