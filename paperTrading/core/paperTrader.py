import csv
import os
import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from pandas import DataFrame

from paperTrading.core import OrderRequestValidator, Executor
from paperTrading.models import Portfolio, OrderRequest, Position, TradeRecord
from paperTrading.enums import OrderType, Action
from api.simpleBinanceApi.fetcher import fetch_klines
from utils import parse_interval, seconds_to_next_boundry

import logging

logger = logging.getLogger("oracle.analysis")
# TODO: cooldown
# TODO: add leverage
# TODO: add trading fees

class PaperTrader:
    def __init__(
            self, symbol: Optional[str], interval: str, lookback: int,
            seconds_to_sleep: int, save_data_path: str,
            strat: object,
            initial_balance: float, risk_per_trade_pct: float, leverage: float = 1,
            buy_conf_threshold: float = 1, sell_conf_threshold: float = -1,
            confirmation_streak_threshold: int = 1, max_positions: Optional[int] = None, drop_oldest_on_max: bool = False,
            block_reentry_until_signal_change: bool = False,
            stop_loss_pct: Optional[float] = None, take_profit_pct: Optional[float] = None,
    ):
        """
        The Portfolio object will be passed if the evaluate() method is containing a parameter named "portfolio"

        :param symbol: If None the OrderRequest will need to return the symbol. If not None the OrderRequest symbols will be overwritten
        :param interval:
        :param lookback:
        :param seconds_to_sleep: How many seconds to sleep between each iteration
        :param save_data_path: Path to save data
        :param confirmation_streak_threshold: How many consecutive signals are required to before accepting the order request/signal.
        :param max_positions: Maximum number of positions, if exceeded the oldest position will be closed
        :param drop_oldest_on_max: If True, automatically close the oldest position when max positions are reached; otherwise, rejects new positions.
        :param block_reentry_until_signal_change: Only enter on signal switch from inactive to active. Prevents multiple entries while the signal stays above the threshold.
        :param initial_balance:
        :param leverage:
        :param risk_per_trade_pct: How much of your total balance to risk per position in percentage
        :param strat: A class containing an evaluate() -> float[-1.0, 1.0] method
        """
        if confirmation_streak_threshold < 1:
            raise ValueError("confirmation_streak_threshold must be at least 1")
        if parse_interval(interval) % seconds_to_sleep != 0:
            raise ValueError("sleep_interval must be divisible by interval")
        if not os.path.exists(save_data_path):
            raise ValueError("save_data_path does not exist")

        self.symbol = symbol
        self.interval = interval
        self.lookback = lookback

        self.seconds_to_sleep = seconds_to_sleep

        self.leverage = leverage  # TODO: add leverage

        self.strat = strat
        self.buy_conf_threshold = buy_conf_threshold
        self.sell_conf_threshold = sell_conf_threshold
        self.stop_loss = stop_loss_pct / 100
        self.take_profit = take_profit_pct / 100

        self.portfolio = Portfolio(
            balance=initial_balance,
            on_position_added=[],
            on_trade_record_added=[self._append_trade_record_to_csv],
            on_order_request_added=[],

        )  # TODO: allow_dept support

        self.ord_req_validator = OrderRequestValidator(
            streak_threshold=confirmation_streak_threshold,
            block_reentry_until_signal_change=block_reentry_until_signal_change,
            default_stop_loss=stop_loss_pct/100,
        )

        self.executor = Executor(
            portfolio=self.portfolio,
            risk_per_trade=risk_per_trade_pct / 100,
            leverage=self.leverage,
            stop_loss=self.stop_loss,
            max_positions=max_positions,
            drop_oldest_on_max=drop_oldest_on_max
        )

        self.df: DataFrame = fetch_klines(symbol=self.symbol, interval=self.interval, limit=self.lookback)
        self.prev_price: Optional[float] = None
        self.csv_path = self._create_csv_path(save_data_path)

    def _create_csv_path(self, save_data_path: str = None) -> str:
        """Create a path to save the data to. Name is based on symbol, interval and timestamp."""
        folder_name = "paperTradingData"
        timestamp_str: str = datetime.now(timezone.utc).strftime('%Y-%m-%d_%Hh-%Mm-%Ss')
        filename = f"{self.strat.__class__.__name__}_{self.symbol}_{self.interval}_{timestamp_str}.csv"

        save_dir = os.path.join(save_data_path, folder_name)
        os.makedirs(save_dir, exist_ok=True)

        save_path = os.path.join(save_dir, filename)

        # Initialize csv file
        with open(save_path, "w", newline="") as f:
            dummy_record = TradeRecord(
                symbol="DUMMY", confidence=0.0, type=OrderType.LONG, action=Action.OPEN,
                entry_price=0.0, qty=0.0, pnl=0.0,
                entry_timestamp=0.0, exit_timestamp=0.0,
                stop_loss=None, take_profit=None
            )
            writer = csv.DictWriter(f, fieldnames=dummy_record.to_dict_for_csv().keys())
            writer.writeheader()

        logger.info(f"Created csv file @ {save_path}")
        return save_path

    def _append_trade_record_to_csv(self, trade_record: TradeRecord) -> None:
        with open(self.csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=trade_record.to_dict_for_csv().keys())
            writer.writerow(trade_record.to_dict_for_csv())

    def _update_df(self):
        """
        Fetch latest candles and update internal DataFrame.
        """
        # 1) Update prev_price before updating df
        self.prev_price = self.df.iloc[-1]["Close"]

        #  # 2) Fetch updated candles
        new = fetch_klines(self.symbol, self.interval, limit=2)
        last_old = self.df.iloc[-1]
        last_new = new.iloc[-1]

        # 3) Overwrite/append new candles
        if last_old["Close Time"] == last_new["Close Time"]:
            self.df.iloc[-1] = last_new
        else:
            logger.debug(f"Updating df, new candle formed. Adding new candle {new.iloc[-1]['Close']}...")
            self.df = (pd.concat([self.df, new.copy()])
                       .drop_duplicates(subset=["Close Time"], keep="last"))
            self.df = self.df.tail(self.lookback)

    def _price_reached(self, target: float) -> bool:
        if self.prev_price is None:
            return False

        curr = self.df.iloc[-1]["Close"]
        crossed = (self.prev_price <= target <= curr) or (self.prev_price >= target >= curr)
        return crossed

    def _build_order_request(self, request: OrderRequest | float) -> OrderRequest | None:
        # If request is already an OrderRequest, set default values if missing
        if type(request) == OrderRequest:
            # Check if symbol is set or can be set
            if request.symbol is None:
                if self.symbol is None:
                    logger.warning(
                        "Symbol is not set and order request has no symbol set, order request will be ignored.")
                    return None
                else:
                    request.symbol = self.symbol
            # Check if stop loss is set or can be set
            if request.stop_loss is None:
                if self.stop_loss is None:
                    logger.warning(
                        "Stop loss is not set and order request has no stop loss set, order request will be ignored.")
                    return None
                else:
                    request.stop_loss = self.stop_loss

            # Check if take profit is set or can be set
            if request.take_profit is None:
                if self.take_profit is None:
                    logger.warning(
                        "Take profit is not set and order request has no take profit set, order request will be ignored.")
                    return None
                else:
                    request.take_profit = self.take_profit

            return request

        # If request is a float, build an OrderRequest
        if request >= self.buy_conf_threshold:
            side = OrderType.LONG
            action = Action.OPEN
        elif request <= self.sell_conf_threshold:
            side = OrderType.SHORT
            action = Action.OPEN
        else:
            return None

        curr_close_price = self.df.iloc[-1]["Close"]
        return OrderRequest(
            symbol=self.symbol,
            timestamp=datetime.now().timestamp(),
            confidence=request,
            type=side,
            action=action,
            entry_price=None,
            qty=None,
            stop_loss=curr_close_price - self.stop_loss * curr_close_price,
            take_profit=curr_close_price + self.take_profit * curr_close_price
        )

    def _handle_order_requests(self) -> None:
        for ord_req in list(self.portfolio.order_requests):

            if ord_req.entry_price is not None and not self._price_reached(ord_req.entry_price):
                continue

            if ord_req.action == Action.OPEN:
                self.executor.open(ord_req, self.df.iloc[-1]["Close"])
            else:
                self.executor.close(ord_req, self.df.iloc[-1]["Close"])

    def _handle_positions(self) -> None:
        for pos in list(self.portfolio.positions):

            curr_close_price: float = self.df.iloc[-1]["Close"]

            if pos.take_profit is not None and self._price_reached(pos.take_profit):
                logger.info(f"Closing position (take profit hit: {pos.take_profit=}/{curr_close_price}): {pos.uuid} => pnl: {pos.pnl(curr_close_price)}")
                self.portfolio.close_position(pos.uuid, curr_close_price)

            elif pos.stop_loss is not None and self._price_reached(pos.stop_loss):
                logger.info(f"Closing position (stop loss hit: {pos.stop_loss=}/{curr_close_price}): {pos.uuid} => pnl: {pos.pnl(curr_close_price)}")
                self.portfolio.close_position(pos.uuid, curr_close_price)

    def _evaluate_and_create_order_request(self, conf: float | OrderRequest) -> None:
        order_request = self._build_order_request(conf)

        if order_request is None:
            self.ord_req_validator.reset_on_neutral()
            return

        elif order_request is not None:
            if self.ord_req_validator.is_valid(order_request):
                self.portfolio.add_order_request(order_request)

    def run(self, start_on_new_candle: bool = False) -> None:
        # startup
        if start_on_new_candle:
            sleep_time = seconds_to_next_boundry(parse_interval(self.interval))
            print(f"Sleeping for {sleep_time} seconds before starting...")
            time.sleep(sleep_time)

        datetime_start = datetime.now()
        while True:
            self._update_df()

            conf: float | OrderRequest = self.strat.evaluate(self.df, portfolio=self.portfolio) # move to _evaluate_and_create_order_request later
            self._evaluate_and_create_order_request(conf)

            self._handle_order_requests()
            self._handle_positions()

            # --- VERBOSE ---
            net_worth = self.portfolio.balance
            for pos in self.portfolio.positions:
                net_worth += pos.total_value(self.df.iloc[-1]["Close"])
            last_networth = net_worth if last_networth is None else last_networth

            print(f"DELTA: {datetime.now() - datetime_start} | OR: {len(self.portfolio.order_requests)} | POS: {len(self.portfolio.positions)} | "
                  f"TR: {len(self.portfolio.trade_records)} | NETWORTH: {net_worth} {"(+)" if net_worth > last_networth else "(-)"}{net_worth - last_networth} | "
                  f"CONF: {conf if isinstance(conf, (float, int)) else conf.confidence} | "
                  f"PRICE: {self.df.iloc[-1]['Close']}", end="\r")
            last_networth = net_worth
            # --- -------- ---
            time.sleep(seconds_to_next_boundry(self.seconds_to_sleep))
