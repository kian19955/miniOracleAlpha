import copy
import os
import time
from datetime import datetime, timezone
from typing import Optional
import atexit

import pandas as pd
from pandas import DataFrame

from paperTrading.models import Portfolio, OrderRequest, Position, TradeRecord
from paperTrading.enums import Side, Action
from api.simpleBinanceApi.fetcher import fetch_klines
from utils import parse_interval, seconds_to_next_boundry

import logging

logger = logging.getLogger("oracle.analysis")



class PaperTrader:
    def __init__(
        self, symbol: str, interval: str, limit: int,
        seconds_to_sleep: int, save_data_path: str,
        initial_balance: float, risk_per_position: float, leverage: float,
        strat: object, buy_conf_threshold: float = 1, sell_conf_threshold: float = -1,
        max_positions: Optional[int] = None, block_reentry_until_signal_reset: bool = False,
        stop_loss: Optional[float] = None, take_profit: Optional[float] = None,
    ):
        """

        :param symbol:
        :param interval:
        :param limit:
        :param seconds_to_sleep: How many seconds to sleep between each iteration
        :param save_data_path: Path to save data
        :param max_positions: Maximum number of positions, if exceeded the oldest position will be closed
        :param block_reentry_until_signal_reset: Only enter on signal switch from inactive to active. Prevents multiple entries while the signal stays above the threshold.
        :param initial_balance:
        :param leverage:
        :param risk_per_position: How much of your total balance to risk per position in percentage
        :param strat: A class containing an evaluate() -> float[-1.0, 1.0] method
        """
        self.symbol = symbol
        self.interval = interval
        self.limit = limit

        self.seconds_to_sleep = seconds_to_sleep
        self.save_data_path = save_data_path
        self.max_positions = max_positions
        self.block_reentry_until_signal_reset = block_reentry_until_signal_reset

        self.leverage = leverage # TODO: add leverage
        self.risk_per_position = risk_per_position

        self.strat = strat
        self.buy_conf_threshold = buy_conf_threshold
        self.sell_conf_threshold = sell_conf_threshold
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.portfolio = Portfolio(balance=initial_balance)

        self.df: DataFrame = fetch_klines(symbol=self.symbol, interval=self.interval, limit=self.limit)

        if parse_interval(self.interval) % self.seconds_to_sleep != 0:
            raise ValueError("sleep_interval must be divisible by interval")
        if not os.path.exists(self.save_data_path):
            raise ValueError("save_data_path does not exist")

        atexit.register(self.save_data)

    def save_data(self):
        logger.info("Saving data...")

        # Create dir and filename
        folder_name = "paperTradingData"
        timestamp_str: str = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"{self.strat.__class__.__name__}_{self.symbol}_{self.interval}_{timestamp_str}.xml"

        save_dir = os.path.join(self.save_data_path, folder_name)
        save_path = os.path.join(save_dir, filename)

        os.makedirs(save_dir, exist_ok=True)

        # Save data
        self.portfolio.save_to_xml(save_path)

        logger.info(f"Successfully saved data to {save_path}")

    def calculate_position_size(self, stop_loss: Optional[float]) -> float:
        """
        Calculate the size of the position using the Position Sizing Formula
        Position Size = (Account Balance × Risk Percentage) / (Stop Loss Percentage × Leverage)

        :return: The size of the position
        """
        if stop_loss is None:
            stop_loss = self.stop_loss

        position_size: float = (self.portfolio.balance * self.risk_per_position) / (stop_loss * self.leverage)
        return position_size

    def _update_df(self):
        new_df = fetch_klines(symbol=self.symbol, interval=self.interval, limit=2)

        if self.df.iloc[-1]["Close Time"] == new_df.iloc[-1]["Close Time"]:
            logger.debug(f"Updating df, new price {new_df.iloc[-1]['Close']}...")
            self.df.iloc[-1] = new_df.iloc[-1]
        elif self.df.iloc[-1]["Close Time"] < new_df.iloc[-1]["Close Time"]:
            logger.info(f"Updating df, new candle formed. Adding new candle {new_df.iloc[-1]['Close']}...")
            self.df.iloc[-1] = new_df.iloc[-2]
            self.df = (
                pd.concat([self.df, new_df.iloc[[-1]]])
                .drop(self.df.index[0])
                .drop_duplicates(subset=["Close Time"], keep="last")
            )

    def _create_order_request(self, conf: float) -> OrderRequest | None:
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

    def _check_price_reached(self, price: float) -> bool:
        candle_1 = self.df.iloc[-2]["Close"]
        candle_2 = self.df.iloc[-1]["Close"]

        if candle_1 <= price <= candle_2 or candle_1 >= price >= candle_2:
            return True

        return False

    def _validate_and_create_position(self, order_request: OrderRequest) -> Position | None:
        if order_request.entry_price is not None:
            if self._check_price_reached(order_request.entry_price):
                return None

        if order_request.qty is None:
            pos_qty = self.calculate_position_size(order_request.stop_loss)
        elif self.portfolio.balance < (order_request.qty * self.df.iloc[-1]["Close"]):
            logger.warning("Not enough balance to execute predefined order, creating order with maximum possible size.")
            pos_qty = self.portfolio.balance / self.df.iloc[-1]["Close"]
        else:
            pos_qty = order_request.qty

        pos: Position = Position(
            root_uuid=order_request.root_uuid,
            symbol=self.symbol,
            timestamp=datetime.now().timestamp(),

            confidence=order_request.confidence,

            entry_price=self.df.iloc[-1]["Close"],
            side=order_request.side,
            action=order_request.action,
            qty=pos_qty,

            stop_loss=order_request.stop_loss,
            take_profit=order_request.take_profit
        )

        return pos

    def _validate_and_close_position(self, ord_req: OrderRequest) -> OrderRequest | None:
        curr_price = self.df.iloc[-1]["Close"]
        if ord_req.entry_price is not None and not self._check_price_reached(ord_req.entry_price):
            return

        open_pos: list[Position] = self.portfolio.find_by_attributes(
            self.portfolio.positions,
            return_copy=False,
            symbol=self.symbol,
            side=ord_req.side
        )
        if not open_pos:
            logger.warning(f"No open positions to close for request {ord_req.uuid}; keeping it pending")
            return

        open_pos.sort(key=lambda p: p.timestamp)
        remaining_qty = ord_req.qty if ord_req.qty is not None else sum(p.qty for p in open_pos)

        for pos in open_pos:
            if remaining_qty <= 0:
                logger.error("Closed more positions than requested.") if remaining_qty < 0 else None
                break

            min_qty = min(pos.qty, remaining_qty)

            if min_qty >= pos.qty:
                logger.info(f"Closing {pos.qty=} @ {curr_price} for position {pos.uuid}")
                self.portfolio.close_position(pos.uuid, closed_at_price=curr_price)
            else:
                logger.info(f"Partially closing {min_qty=} @ {curr_price} for position {pos.uuid}")
                temp_pos = copy.copy(pos)
                temp_pos.qty = min_qty
                tr = TradeRecord.from_position(temp_pos, closed_at_price=curr_price)
                self.portfolio.trade_records.append(tr)
                pos.qty -= min_qty

            remaining_qty -= min_qty

        if ord_req.qty is not None and remaining_qty > 0:
            logger.warning(
                f"Requested to close {ord_req.qty}, "
                f"but only filled partially. Remaining qty: {ord_req.qty - remaining_qty}"
            )

        return ord_req

    def _handle_order_requests(self) -> None:
        for ord_req in self.portfolio.order_requests:

            if ord_req.action == Action.OPEN:
                new_pos: Position | None = self._validate_and_create_position(ord_req)

                if new_pos is not None:
                    logger.info(f"Opening position: {new_pos}")
                    self.portfolio.add_position(new_pos)
                else:
                    logger.info(f"Order request added to pending order requests: {ord_req}")
                    self.portfolio.add_order_request(ord_req)

            else:
                ord_req: OrderRequest | None = self._validate_and_close_position(ord_req)

                if ord_req is not None:
                    logger.info(f"Closing order request {ord_req.uuid}")
                    self.portfolio.rmv_order_request(ord_req.uuid)

    def _handle_positions(self) -> None:
        if self.max_positions is not None and len(self.portfolio.positions) > self.max_positions:
            logger.info(f"Closing oldest position: {self.portfolio.positions[0]}")
            self.portfolio.close_position(self.portfolio.positions[0].uuid)

        for pos in self.portfolio.positions:

            curr_close_price: float = self.df.iloc[-1]["Close"]

            if pos.take_profit is not None and self._check_price_reached(pos.take_profit):
                logger.info(f"Closing position (take profit hit: {pos.take_profit=}/{curr_close_price}): {pos}")
                self.portfolio.close_position(pos.uuid, curr_close_price)

            elif pos.stop_loss is not None and self._check_price_reached(pos.stop_loss):
                logger.info(f"Closing position (stop loss hit: {pos.stop_loss=}/{curr_close_price}): {pos}")
                self.portfolio.close_position(pos.uuid, curr_close_price)

    def run(self) -> None:
        time.sleep(seconds_to_next_boundry(parse_interval(self.interval)))
        position_entered: bool = False

        while True:
            self._update_df()

            conf: float | OrderRequest = self.strat.evaluate(self.df)
            if type(conf) != OrderRequest:
                order_request: OrderRequest | None = self._create_order_request(conf)
            else:
                order_request = conf

            if order_request is None:
                position_entered = False

            elif order_request is not None and (not self.block_reentry_until_signal_reset or not position_entered):
                position_entered = True
                self.portfolio.add_order_request(order_request)

            self._handle_order_requests()
            self._handle_positions()

            time.sleep(seconds_to_next_boundry(self.seconds_to_sleep))
