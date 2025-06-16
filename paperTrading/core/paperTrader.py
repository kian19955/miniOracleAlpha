import copy
import os
import time
from datetime import datetime, timezone
from typing import Optional
import atexit

import pandas as pd
from pandas import DataFrame

from paperTrading.core import OrderRequestValidator, Executor
from paperTrading.models import Portfolio, OrderRequest, Position, TradeRecord
from paperTrading.enums import Side, Action
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
            buy_conf_threshold: float = 1, sell_conf_threshold: float = -1, confirmation_streak_threshold: int = 1,
            max_positions: Optional[int] = None, block_reentry_until_signal_change: bool = False,
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
        self.save_data_path = save_data_path


        self.leverage = leverage  # TODO: add leverage

        self.strat = strat
        self.buy_conf_threshold = buy_conf_threshold
        self.sell_conf_threshold = sell_conf_threshold
        self.stop_loss = stop_loss_pct / 100
        self.take_profit = take_profit_pct / 100

        self.portfolio = Portfolio(balance=initial_balance)  # TODO: allow_dept support

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
        )

        self.df: DataFrame = fetch_klines(symbol=self.symbol, interval=self.interval, limit=self.lookback)
        self.prev_price: Optional[float] = None

        atexit.register(self.save_data)

    def save_data(self):
        logger.info("Saving data...")

        # Create dir and filename
        folder_name = "paperTradingData"
        timestamp_str: str = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"{self.strat.__class__.__name__}_{self.symbol}_{self.interval}_{timestamp_str}.csv"

        save_dir = os.path.join(self.save_data_path, folder_name)
        save_path = os.path.join(save_dir, filename)

        os.makedirs(save_dir, exist_ok=True)

        # Save data
        self.portfolio.save_to_csv(save_path)

        logger.info(f"Successfully saved data to {save_path}")

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

    def _build_order_request(self, conf: float) -> OrderRequest | None:
        if conf >= self.buy_conf_threshold:
            side = Side.LONG
            action = Action.OPEN
        elif conf < self.sell_conf_threshold:
            side = Side.SHORT
            action = Action.OPEN
        else:
            return None

        curr_close_price = self.df.iloc[-1]["Close"]
        return OrderRequest(
            symbol=self.symbol,
            timestamp=datetime.now().timestamp(),
            confidence=conf,
            side=side,
            action=action,
            entry_price=None,
            qty=None,
            stop_loss=curr_close_price - self.stop_loss * curr_close_price,
            take_profit=curr_close_price + self.take_profit * curr_close_price
        )

    def _handle_order_requests(self) -> None:
        for ord_req in self.portfolio.order_requests:

            if ord_req.entry_price is not None and not self._price_reached(ord_req.entry_price):
                continue

            if ord_req.action == Action.OPEN:
                self.executor.open(ord_req, self.df.iloc[-1]["Close"])
            else:
                self.executor.close(ord_req, self.df.iloc[-1]["Close"])

    def _handle_positions(self) -> None:
        for pos in self.portfolio.positions:

            curr_close_price: float = self.df.iloc[-1]["Close"]

            if pos.take_profit is not None and self._price_reached(pos.take_profit):
                logger.info(f"Closing position (take profit hit: {pos.take_profit=}/{curr_close_price}): {pos.uuid} => pnl: {pos.pnl(curr_close_price)}")
                self.portfolio.close_position(pos.uuid, curr_close_price)

            elif pos.stop_loss is not None and self._price_reached(pos.stop_loss):
                logger.info(f"Closing position (stop loss hit: {pos.stop_loss=}/{curr_close_price}): {pos.uuid} => pnl: {pos.pnl(curr_close_price)}")
                self.portfolio.close_position(pos.uuid, curr_close_price)

    def _evaluate_and_create_order_request(self, conf: float | OrderRequest) -> None:
        if type(conf) != OrderRequest:
            order_request: OrderRequest | None = self._build_order_request(conf)
        else:
            order_request = conf
            # Check if symbol is set or can be set
            if order_request.symbol is None:
                if self.symbol is None:
                    logger.warning(
                        "Symbol is not set and order request has no symbol set, order request will be ignored.")
                    order_request = None
                else:
                    order_request.symbol = self.symbol

        if order_request is None:
            self.ord_req_validator.reset_on_neutral()
            return

        elif order_request is not None:
            if self.ord_req_validator.is_valid(order_request):
                return

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

            print(f"DELTA: {datetime.now() - datetime_start} | OR: {len(self.portfolio.order_requests)} | POS: {len(self.portfolio.positions)} | "
                  f"TR: {len(self.portfolio.trade_records)} | NETWORTH: {net_worth} | CONF: {conf if isinstance(conf, (float, int)) else conf.confidence} | "
                  f"PRICE: {self.df.iloc[-1]['Close']}", end="\r")
            # --- -------- ---
            time.sleep(seconds_to_next_boundry(self.seconds_to_sleep))
