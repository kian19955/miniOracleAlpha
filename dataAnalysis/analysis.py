from typing import Optional

import pandas as pd
from numpy import std

from constants import bt_data_dir_path

balance = 100


def analyze(
        target_filename: str,
        bt_df: Optional[pd.DataFrame] = None,
        trade_long: bool = True,
        trade_short: bool = True,
        print_details: bool = True
) -> dict[str, Optional[float]]:
    # Initialize empty DataFrame if no data provided
    if bt_df is None:
        bt_df = pd.read_csv(f"{bt_data_dir_path}/{target_filename}")
        bt_df.set_index("timestamp", inplace=True)
        bt_df.index = pd.to_datetime(bt_df.index)

    # Safe division helper with null handling
    def safe_divide(numerator: float, denominator: float, zero_override: bool = False) -> Optional[float]:
        if denominator == 0:
            return 0.0 if zero_override else None
        return numerator / denominator

    # Pre-filter orders and initialize containers
    orders = bt_df[bt_df["type"].notnull()]
    buys = orders[orders["type"] == "buy"] if trade_long else pd.DataFrame()
    sells = orders[orders["type"] == "sell"] if trade_short else pd.DataFrame()

    # Calculate profit history
    profit_history = {}
    last_valid_liquidity = None
    current_position = None  # 'long', 'short', or None

    for idx, row in orders.iterrows():
        if row["type"] == "buy":
            if current_position == "short":
                # Close short position
                if last_valid_liquidity is not None:
                    profit_history[idx] = safe_divide(row["liquidity"], last_valid_liquidity) - 1
                # Open long position
                last_valid_liquidity = row["liquidity"] if trade_long else None
                current_position = "long" if trade_long else None
            elif current_position is None and trade_long:
                # Open long position
                last_valid_liquidity = row["liquidity"]
                current_position = "long"
        elif row["type"] == "sell":
            if current_position == "long":
                # Close long position
                if last_valid_liquidity is not None:
                    profit_history[idx] = safe_divide(row["liquidity"], last_valid_liquidity) - 1
                # Open short position
                last_valid_liquidity = row["liquidity"] if trade_short else None
                current_position = "short" if trade_short else None
            elif current_position is None and trade_short:
                # Open short position
                last_valid_liquidity = row["liquidity"]
                current_position = "short"

    # Calculate final metrics
    metrics = {
        "total_buys": len(buys),
        "total_sells": len(sells),
        "total_orders": len(orders),
        "total_fee_buy": buys["fee"].sum(),
        "total_fee_sell": sells["fee"].sum(),
        "total_fee_orders": orders["fee"].sum(),
    }

    # Calculate averages with business-appropriate null handling
    avg_metrics = {
        "avg_fee_per_buy": safe_divide(metrics["total_fee_buy"], metrics["total_buys"], zero_override=True),
        "avg_fee_per_sell": safe_divide(metrics["total_fee_sell"], metrics["total_sells"], zero_override=True),
        "avg_fee_orders": safe_divide(metrics["total_fee_orders"], metrics["total_orders"], zero_override=True),
    }
    metrics.update(avg_metrics)

    # Calculate profit metrics
    profit_metrics = {
        "total_profit": bt_df["liquidity"].iloc[-1] - bt_df["liquidity"].iloc[0],
        "avg_profit": safe_divide(
            bt_df["liquidity"].iloc[-1] - bt_df["liquidity"].iloc[0],
            metrics["total_orders"],
            zero_override=True
        ),
        "std_profit": std(list(profit_history.values()), ddof=0) if profit_history else None,
    }
    metrics.update(profit_metrics)

    # Calculate complex ratios with proper null handling
    ratios = {
        "sharpe_ratio": safe_divide(profit_metrics["avg_profit"], profit_metrics["std_profit"])
        if (profit_metrics["avg_profit"] and profit_metrics["std_profit"])
        else None,

        "percentage_fee_of_net_worth": safe_divide(
            metrics["total_fee_orders"],
            bt_df["liquidity"].iloc[-1] * balance
        ),

        "percentage_fee_of_profit": safe_divide(
            metrics["total_fee_orders"],
            profit_metrics["total_profit"] * balance
        ) if profit_metrics["total_profit"] else None,
    }
    metrics.update(ratios)

    # Print formatted summary
    if print_details:
        print("\n=== Trading Performance Summary ===")
        print(f"Orders: {metrics['total_orders']} (Buys: {metrics['total_buys']}, Sells: {metrics['total_sells']})")
        print(f"Total Profit: {metrics['total_profit']:.2f}")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio'] or 'N/A'}")
        print(
            f"Fees: {metrics['total_fee_orders']:.2f} (Net Worth Impact: {metrics['percentage_fee_of_net_worth'] or 'N/A':.2%})")
        print("\n=== Details ===")
        for key, value in metrics.items():
            print(f"{key}: {value or 'N/A'}")

    return metrics
