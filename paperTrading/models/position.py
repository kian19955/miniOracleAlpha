from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from paperTrading.enums import OrderAction
from paperTrading.models import BaseTradingData

@dataclass
class Position(BaseTradingData):
    """
    :param uuid: universally unique identifier (uuid.uuid4())
    :param symbol: e.g. "BTCUSDT"
    :param creation_time: datetime at which the asset was bought, timezone is UTC

    :param confidence: confidence level of the OrderRequest (-1.0 to 1.0) where -1 = max sell, 0 = neutral, +1 = max buy

    :param entry_price: price at which the asset was bought
    :param direction: Side.LONG or Side.SHORT
    :param action: Action.SELL or Action.BUY
    :param qty: quantity of the asset

    :param stop_loss: the price where the stop loss is placed
    :param take_profit: the price where the take profit is placed
    """

    def total_value(self, closed_at_price: float) -> float:
        if self.action == OrderAction.CLOSE:
            return 0
        return (self.entry_price * self.qty) + self.pnl(closed_at_price)

    def holding_period_reached(self) -> bool:
        if self.max_holding_period is None:
            return False
        else:
            return (self.creation_time + self.max_holding_period) <= datetime.now(timezone.utc)

    @classmethod
    def from_order_request(
            cls,
            order_request: 'OrderRequest',
            **pos_kwargs,
    ) -> 'Position':
        return Position(
            root_uuid=pos_kwargs.get('root_uuid', order_request.root_uuid),
            symbol=pos_kwargs.get('symbol', order_request.symbol),
            creation_time=pos_kwargs.get('creation_time', order_request.creation_time),
            max_holding_period=pos_kwargs.get('max_holding_period', order_request.max_holding_period),
            confidence=pos_kwargs.get('confidence', order_request.confidence),
            entry_price=pos_kwargs.get('entry_price', order_request.entry_price),
            direction=pos_kwargs.get('type', order_request.direction),
            action=pos_kwargs.get('action', order_request.action),
            qty=pos_kwargs.get('qty', order_request.qty),
            stop_loss=pos_kwargs.get('stop_loss', order_request.stop_loss),
            take_profit=pos_kwargs.get('take_profit', order_request.take_profit),
            is_maker=pos_kwargs.get('is_maker', order_request.is_maker),
            commission=pos_kwargs.get('execution_fee', order_request.commission),
        )