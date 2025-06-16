import copy
from typing import Optional
import logging
from paperTrading.models import Portfolio, OrderRequest, Position, TradeRecord

logger = logging.getLogger("oracle.analysis")

class Executor:
    """
    Handles turning validated OrderRequests into Positions,
    enforcing max_positions, and closing positions on requests.
    """
    def __init__(
        self,
        portfolio: Portfolio,
        stop_loss: float,
        risk_per_trade: float,
        leverage: float,
        max_positions: Optional[int] = None,
    ):
        self.portfolio = portfolio
        self.stop_loss = stop_loss
        self.risk_per_trade = risk_per_trade
        self.leverage = leverage
        self.max_positions = max_positions

    def calculate_position_size(self, ord_req: OrderRequest, current_price: float) -> float:
        """
        Compute position size based on risk.

        :param ord_req: OrderRequest instance
        :param current_price: Current close. df.iloc[-1]["Close"]
        :return: Quantity to trade.
        """
        # Calculate stop loss from absolute to percentage
        if ord_req.stop_loss is not None:
            if ord_req.entry_price is None:
                entry_price = current_price
            else:
                entry_price = ord_req.entry_price

            stop_loss_ratio = abs(ord_req.stop_loss - entry_price) / entry_price
        else:
            stop_loss_ratio = self.stop_loss

        risk_amount = self.portfolio.balance * self.risk_per_trade
        loss_per_unit = abs(stop_loss_ratio - current_price)
        return (risk_amount / loss_per_unit) * self.leverage

    def open(self, order_request: OrderRequest, current_price: float) -> Optional[Position]:
        # determine qty if not provided
        if order_request.qty is None:
            qty = self.calculate_position_size(order_request, current_price)
        else:
            total_cost = order_request.qty * current_price
            if total_cost > self.portfolio.balance:
                logger.warning(
                    "Insufficient balance: resizing order to max affordable qty"
                )
                qty = self.portfolio.balance / current_price
            else:
                qty = order_request.qty

        pos = Position(
            root_uuid=order_request.root_uuid,
            symbol=order_request.symbol,
            timestamp=order_request.timestamp,
            confidence=order_request.confidence,
            entry_price=current_price,
            side=order_request.side,
            action=order_request.action,
            qty=qty,
            stop_loss=order_request.stop_loss,
            take_profit=order_request.take_profit,
        )

        # enforce max_positions
        if (
            self.max_positions is not None
            and len(self.portfolio.positions) + 1 > self.max_positions
        ):
            # since portfolio.positions maintains insertion order (oldest first), the first element is the oldest
            oldest = self.portfolio.positions[0]
            pnl = oldest.pnl(current_price)
            logger.info(
                f"Max positions reached; closing oldest {oldest.uuid} PnL={pnl}"
            )
            self.portfolio.close_position(oldest.uuid, closed_at_price=current_price)

        # add to portfolio and remove its order_request
        logger.info(f"Opening position: {pos}")
        self.portfolio.add_position(pos)
        self.portfolio.rmv_order_request(order_request.uuid)
        return pos

    def close(self, order_request: OrderRequest, current_price: float) -> Optional[OrderRequest]:
        # find matching open positions
        open_positions = self.portfolio.find_by_attributes(
            self.portfolio.positions,
            return_copy=False,
            symbol=order_request.symbol,
            side=order_request.side,
        )

        if not open_positions:
            logger.warning(
                f"No open positions to close for {order_request.uuid}; dropping request"
            )
            self.portfolio.rmv_order_request(order_request.uuid)
            return

        # compute remaining qty
        remaining = (
            order_request.qty
            if order_request.qty is not None
            else sum(p.qty for p in open_positions)
        )

        # sort by timestamp to process oldest closes first
        for pos in sorted(open_positions, key=lambda p: p.timestamp):
            if remaining <= 0:
                logger.error("Closed more positions than requested.") if remaining < 0 else None # TODO: for check (debug)
                break

            take: float = min(pos.qty, remaining)
            if take >= pos.qty:
                logger.info(f"Closing full pos {pos.uuid} PnL={pos.pnl(current_price)}")
                self.portfolio.close_position(pos.uuid, closed_at_price=current_price)
            else:
                partial = pos.copy()
                partial.qty = take

                tr = TradeRecord.from_position(partial, closed_at_price=current_price)
                logger.info(f"Closing partial {take=} PnL={tr.pnl} for {pos.uuid}")
                self.portfolio.trade_records.append(tr)

                pos.qty -= take
            remaining -= take

        if order_request.qty is not None and remaining > 0:
            logger.warning(
                f"Could not fully fill close request {order_request.uuid}; leftover={remaining}"
            )

        # remove the request
        self.portfolio.rmv_order_request(order_request.uuid)