from typing import Optional, Hashable

import pandas as pd
from pandas import DataFrame, read_csv
from numpy import std, nan

from constants import bt_data_dir_path

balance = 100


def analyze(
        target_filename: str,
        bt_df: Optional[DataFrame] = None,
        trade_long: bool = True,
        trade_short: bool = True,
        print_info: bool = True
) -> dict[str, float]:
    if bt_df is None:
        bt_df: DataFrame = read_csv(f"{bt_data_dir_path}/{target_filename}")
        bt_df.set_index("timestamp", inplace=True)
        bt_df.index = pd.to_datetime(bt_df.index)

    order_df: DataFrame = bt_df[bt_df["type"].notnull()]
    buy_df: DataFrame = bt_df[bt_df["type"] == "buy"]
    sell_df: DataFrame = bt_df[bt_df["type"] == "sell"]

    profit_his: dict[Hashable, float] = {}
    last_liquidity: Optional[float] = None

    for index, order in order_df.iterrows():
        if trade_short and order.iloc[1] == "sell" or trade_long and order.iloc[1] == "buy":
            if last_liquidity is not None:
                profit_his[index] = (order.iloc[4] / last_liquidity) - 1

        if order.iloc[1] == "sell" and trade_short or order.iloc[1] == "buy" and trade_long:
            last_liquidity = order.iloc[4]

    if not order_df.empty:
        profit_his[bt_df.index[-1]] = (bt_df.iloc[-1]["liquidity"] / last_liquidity) - 1

    total_buys = len(buy_df)
    total_sells = len(sell_df)
    total_orders = total_buys + total_sells

    total_fee_buy: float = sum(buy_df["fee"])
    total_fee_sell: float = sum(sell_df["fee"])
    avg_fee_per_buy: float = total_fee_buy / total_buys if total_buys > 0 else nan
    avg_fee_per_sell: float = total_fee_sell / total_sells if total_sells > 0 else nan

    total_fee_orders: float = total_fee_buy + total_fee_sell
    avg_fee_orders: float = total_fee_orders / total_orders if total_orders > 0 else nan

    total_profit: float = bt_df.iloc[-1]["liquidity"] - bt_df.iloc[0]["liquidity"]
    avg_profit: float = total_profit / total_orders

    std_profit: float = std(list(profit_his.values()))

    sharpe_ratio = avg_profit / std_profit if std_profit > 0 else -100

    percentage_fee_of_net_worth: float = (total_fee_orders / (bt_df["liquidity"].iloc[-1] * balance))
    percentage_fee_of_profit: float = 0.0
    if total_orders > 0:
        percentage_fee_of_profit: float = (
                total_fee_orders / ((bt_df["liquidity"].iloc[-1] - bt_df["liquidity"].iloc[0]) * balance))

    if print_info:
        print(f"Total buys: {total_buys:.3f}, "
              f"Total sells: {total_sells:.3f}, "
              f"Total orders: {total_orders:.3f}")
        print(f"Total fee buy: {total_fee_buy:.3f}, "
              f"Total fee sell: {total_fee_sell:.3f}, "
              f"Total fee orders: {total_fee_orders:.3f}")
        print(f"Average fee per buy: {avg_fee_per_buy:.3f}, "
              f"Average fee per sell: {avg_fee_per_sell:.3f}, "
              f"Average fee per order: {avg_fee_orders:.3f}")
        print(f"Percentage fee of net worth: {percentage_fee_of_net_worth:.3%}, "
              f"Percentage fee of profit: {percentage_fee_of_profit:.3%}")
        print(f"Profit History")
        for time, profit in profit_his.items():
            print(f"{time}: {profit:.3f}")
        print(f"Total Profit: {total_profit:.3%}, Average Profit per order: {avg_profit:.3%}")
        print(f"Standard Deviation of Profit: {std_profit:.3%}")
        print(f"Sharpe Ratio: {sharpe_ratio:.3f}")

    return {
        "total_buys": total_buys,
        "total_sells": total_sells,
        "total_orders": total_orders,
        "total_fee_buy": total_fee_buy,
        "total_fee_sell": total_fee_sell,
        "avg_fee_per_buy": avg_fee_per_buy,
        "avg_fee_per_sell": avg_fee_per_sell,
        "total_fee_orders": total_fee_orders,
        "avg_fee_orders": avg_fee_orders,
        "percentage_fee_of_net_worth": percentage_fee_of_net_worth,
        "percentage_fee_of_profit": percentage_fee_of_profit,
        "total_profit": total_profit,
        "avg_profit": avg_profit,
        "std_profit": std_profit,
        "sharpe_ratio": sharpe_ratio
    }
