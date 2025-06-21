from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID

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
    :param type: Side.LONG or Side.SHORT
    :param action: Action.SELL or Action.BUY
    :param qty: quantity in base units, if none the Simulator will decide

    :param stop_loss: the price where the stop loss should be placed
    :param take_profit: the price where the take profit should be placed
    """
    root_uuid: UUID = field(default_factory=uuid4, init=False)
    expiration_time: Optional[datetime] = None

    def is_expired(self):
        if self.expiration_time is None:
            return False
        else:
            return self.expiration_time <= datetime.now()

