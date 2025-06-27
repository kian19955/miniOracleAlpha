from typing import Optional
import logging

from pandas import DataFrame

from api.simpleBinanceApi import fetch_order_book
from paperTrading.models import Portfolio, OrderRequest, Position, TradeRecord
from paperTrading.reporters import ContextBuilder
from paperTrading.enums import PositionDirection, OrderType, OrderAction

logger = logging.getLogger("oracle.analysis")


class Executor:
    """
    Handles turning validated OrderRequests into Positions,
    enforcing max_positions, and closing positions on requests.
    """

    def __init__(
            self,
            portfolio: Portfolio,
            ctx_builder: ContextBuilder,
            stop_loss: float,
            risk_per_trade: float,
            taker_fee: float,
            maker_fee: float,
            leverage: float,
            max_positions: Optional[int] = None,
            drop_oldest_on_max: bool = False,
    ):
        self.portfolio = portfolio
        self.ctx_builder = ctx_builder
        self.stop_loss = stop_loss
        self.risk_per_trade = risk_per_trade
        self.taker_fee = taker_fee
        self.maker_fee = maker_fee
        self.leverage = leverage
        self.max_positions = max_positions
        self.drop_oldest_on_max = drop_oldest_on_max

    def _calculate_position_size(self, ord_req: OrderRequest, entry_price: float) -> float:
        """
        Compute position size based on risk.

        :param ord_req: OrderRequest instance
        :param entry_price: Current close_pos. df.iloc[-1]["Close"]
        :return: Quantity to trade.
        """
        # Calculate stop loss from absolute to percentage
        if ord_req.stop_loss is not None:
            stop_loss_ratio = abs(ord_req.stop_loss - entry_price) / entry_price
        else:
            stop_loss_ratio = self.stop_loss

        if stop_loss_ratio <= 0:
            raise ValueError("Stop‑loss must be different from entry price to compute size")

        risk_amount = self.portfolio.balance * self.risk_per_trade
        risk_amount = risk_amount / (
                    stop_loss_ratio * self.leverage)  # TODO: REWRITE due to issue: sl: 0.01, therefor risk_amount*100 > balance each time

        # --- ISSUE FIX TEMP ---
        if min(risk_amount, self.portfolio.balance) == self.portfolio.balance:
            risk_amount = self.portfolio.balance
            logger.warning(f"Risk amount is greater than balance; using total balance instead (ISSUE): {risk_amount}")
        # -----------------------

        return risk_amount / entry_price

    def _handle_cost_exceeding_balance(self, ord_req: OrderRequest, entry_price: float) -> bool:
        total_cost = ord_req.qty * ord_req.entry_price
        if total_cost > self.portfolio.balance:
            logger.warning(
                "Insufficient balance: resizing order to max affordable qty"
            )
            ord_req.qty = self.portfolio.balance / ord_req.entry_price

    def _handle_commissions(self, ord_req: OrderRequest) -> None:
        if not ord_req.should_execute_order(ord_req.entry_price):
            ord_req.is_maker = True
        else:
            ord_req.is_maker = False

        commission: float = ord_req.qty * ord_req.entry_price * (self.maker_fee if ord_req.is_maker else self.taker_fee)

        ord_req.commission += commission
        ord_req.qty = ord_req.qty - (commission / ord_req.entry_price)

        self.portfolio.balance -= ord_req.commission
        self._handle_cost_exceeding_balance(ord_req, ord_req.entry_price)

    def open_pos(self, order_request: OrderRequest, current_price: float) -> Optional[Position]:
        exec_price = order_request.entry_price if order_request.entry_price is not None else current_price
        order_request.entry_price = exec_price

        # 1) Enforce max_positions
        if self.max_positions is not None and len(self.portfolio.positions) + 1 > self.max_positions:
            if not self.drop_oldest_on_max:
                logger.info(
                    f"Max positions reached; dropping request to {order_request.action} {order_request.direction} for {order_request.symbol}")
                self.portfolio.rmv_order_request(order_request.uuid)
                return None

            # since portfolio.positions maintains insertion order (FIFO), the first element is the oldest
            oldest = self.portfolio.positions[0]
            logger.info(
                f"Max positions reached; closing oldest {oldest.uuid} @ {exec_price} => PnL={oldest.pnl(exec_price)}"
            )
            self.portfolio.close_position(
                oldest.uuid,
                closed_at_price=current_price,
                closing_reason="Max positions reached"
            )

        # 2) Determine how many units to buy/sell
        if order_request.qty is None:
            order_request.qty = self._calculate_position_size(order_request, exec_price)
        self._handle_cost_exceeding_balance(order_request, exec_price)

        # 3) Handle commissions
        self._handle_commissions(order_request)

        # 4) Create position
        pos = Position.from_order_request(
            order_request=order_request,
        )

        # 5) Add to portfolio and remove its order_request
        logger.info(f"Opening position: {pos}")
        self.portfolio.add_position(pos, order_request.uuid)
        self.ctx_builder.add_new_position(pos.uuid)
        return pos

    def close_pos(self, order_request: OrderRequest, current_price: float) -> None:
        exec_price = order_request.entry_price if order_request.entry_price is not None else current_price
        order_request.entry_price = exec_price

        # find matching open_pos positions
        open_positions = self.portfolio.find_by_attributes(
            self.portfolio.positions,
            return_copy=False,
            symbol=order_request.symbol,
            direction=order_request.direction,
            type=OrderAction.OPEN,
        )

        if not open_positions:
            logger.warning(
                f"No open_pos positions to close_pos for {order_request.uuid}; dropping request"
            )
            self.portfolio.rmv_order_request(order_request.uuid)
            return

        # compute remaining qty
        total_to_close: float = (
            order_request.qty
            if order_request.qty is not None
            else sum(p.qty for p in open_positions)
        )
        order_request.qty = total_to_close
        remaining: float = total_to_close

        self._handle_commissions(order_request)
        fee_per_unit = order_request.commission / total_to_close
        # We want to migrate the fee to each of the positions to close respectively
        # Therefor we add the closing fee to balance as self.portfolio.(partially_)close_position will subtract it
        # Remaining(=> not enough positions to close) fee will not be subtracted, as those positions never existed
        self.portfolio.balance += order_request.commission

        # sort by timestamp to process oldest closes first
        for pos in sorted(open_positions, key=lambda p: p.creation_time):
            if remaining <= 0:
                logger.error(
                    "Closed more positions than requested.") if remaining < 0 else None  # TODO: for check (debug)
                break

            take: float = min(pos.qty, remaining)
            closing_fee = take * fee_per_unit

            if take >= pos.qty:
                logger.info(f"Closing full pos {pos.uuid} PnL={pos.pnl(exec_price)}")
                tr_uuid = self.portfolio.close_position(
                    pos.uuid,
                    closed_at_price=exec_price,
                    closing_reason="Full Close - Action.CLOSE",
                    closing_fee=closing_fee
                )
                self.ctx_builder.add_new_trade_record(tr_uuid)
            else:
                partial_tr_uuid = self.portfolio.partially_close_position(
                    pos.uuid,
                    fill_qty=take,
                    closed_at_price=exec_price,
                    closing_reason="Partial Close - Action.CLOSE",
                    closing_fee=closing_fee
                )
                partial_tr = self.portfolio.find_by_attributes(
                    self.portfolio.trade_records,
                    uuid=partial_tr_uuid
                )[0]
                logger.info(f"Closing partially pos {pos.uuid}, partial PnL={partial_tr.pnl}")

            remaining -= take

        if order_request.qty is not None and remaining > 0:
            logger.warning(
                f"Could not fully fill close_pos request {order_request.root_uuid}; leftover={remaining}"
            )

        # Close the close_position
        self.portfolio.rmv_order_request(order_request.uuid)
