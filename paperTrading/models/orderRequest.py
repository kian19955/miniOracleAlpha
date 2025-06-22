from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID

from paperTrading.enums import OrderType, PositionDirection
from paperTrading.models import BaseTradingData


@dataclass
class OrderRequest(BaseTradingData):
    """
    :param uuid: universally unique identifier (uuid.uuid4())
    :param symbol: e.g. "BTCUSDT" if None MAY be handled by the simulator

    :param creation_time: datetime at which the OrderRequest was created, timezone is UTC
    :param expiration_time: Datetime at which the OrderRequest expires

    :param confidence: confidence level (-1.0 to 1.0) where -1 = max sell, 0 = neutral, +1 = max buy, can be of type float

    :param entry_price: price for limit orders, if none will buy/sell at current price
    :param direction: Side.LONG or Side.SHORT
    :param action: Action.SELL or Action.BUY
    :param qty: quantity in base units, if none the Simulator will decide

    :param stop_loss: the price where the stop loss should be placed
    :param take_profit: the price where the take profit should be placed
    """
    expiration_time: Optional[datetime] = None

    def __post_init__(self):
        super().__post_init__()
        if self.entry_price is None:
            self.type = OrderType.MARKET
        else:
            self.type = OrderType.LIMIT

    def should_execute_order(self, price: float):
        """
        Checks if the limit price has been reached

        :param price:
        :return: Returns True if the limit price has been reached or no limit is set
        """
        if self.type == OrderType.LIMIT:
            if self.direction == PositionDirection.LONG:
                return self.entry_price <= price
            else:
                return self.entry_price >= price
        else:
            return True

    def is_expired(self):
        if self.expiration_time is None:
            return False
        else:
            return self.expiration_time <= datetime.now()

    @classmethod
    def modify_order_request(cls, order_request: 'OrderRequest', create_copy: bool = True, **order_request_kwargs):
        if create_copy:
            return cls(
                root_uuid=order_request_kwargs.get('root_uuid', order_request.root_uuid),
                symbol=order_request_kwargs.get('symbol', order_request.symbol),
                expiration_time=order_request_kwargs.get('expiration_time', order_request.expiration_time),
                creation_time=order_request_kwargs.get('creation_time', order_request.creation_time),
                max_holding_period=order_request_kwargs.get('max_holding_period', order_request.max_holding_period),
                confidence=order_request_kwargs.get('confidence', order_request.confidence),
                entry_price=order_request_kwargs.get('entry_price', order_request.entry_price),
                direction=order_request_kwargs.get('direction', order_request.direction),
                action=order_request_kwargs.get('action', order_request.action),
                qty=order_request_kwargs.get('qty', order_request.qty),
                stop_loss=order_request_kwargs.get('stop_loss', order_request.stop_loss),
                take_profit=order_request_kwargs.get('take_profit', order_request.take_profit),
                is_maker=order_request_kwargs.get('is_maker', order_request.is_maker),
                commission=order_request_kwargs.get('execution_fee', order_request.execution_fee)
            )
        else:
            order_request.root_uuid = order_request_kwargs.get('root_uuid', order_request.root_uuid)
            order_request.symbol = order_request_kwargs.get('symbol', order_request.symbol)
            order_request.expiration_time = order_request_kwargs.get('expiration_time', order_request.expiration_time)
            order_request.creation_time = order_request_kwargs.get('creation_time', order_request.creation_time)
            order_request.max_holding_period = order_request_kwargs.get('max_holding_period', order_request.max_holding_period)
            order_request.confidence = order_request_kwargs.get('confidence', order_request.confidence)
            order_request.entry_price = order_request_kwargs.get('entry_price', order_request.entry_price)
            order_request.direction = order_request_kwargs.get('direction', order_request.direction)
            order_request.action = order_request_kwargs.get('action', order_request.action)
            order_request.qty = order_request_kwargs.get('qty', order_request.qty)
            order_request.stop_loss = order_request_kwargs.get('stop_loss', order_request.stop_loss)
            order_request.take_profit = order_request_kwargs.get('take_profit', order_request.take_profit)
            order_request.is_maker = order_request_kwargs.get('is_maker', order_request.is_maker)
            order_request.execution_fee = order_request_kwargs.get('execution_fee', order_request.execution_fee)