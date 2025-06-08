from dataclasses import dataclass, field
from uuid import uuid4, UUID

from paperTrading.models import BaseTradingData


@dataclass
class OrderRequest(BaseTradingData):
    """
    :param uuid: universally unique identifier (uuid.uuid4())
    :param symbol: e.g. "BTCUSDT"
    :param timestamp: unix timestamp, timezone is UTC

    :param confidence: confidence level (-1.0 to 1.0) where -1 = max sell, 0 = neutral, +1 = max buy, can be of type float

    :param entry_price: price for limit orders, if none will buy/sell at current price
    :param side: Side.LONG or Side.SHORT
    :param action: Action.SELL or Action.BUY
    :param qty: quantity in base units, if none the Simulator will decide

    :param stop_loss: the price where the stop loss should be placed
    :param take_profit: the price where the take profit should be placed
    """

    root_uuid: UUID = field(default_factory=uuid4, init=False)

    def __post_init__(self):
        if self.entry_price is None:
            return

        if self.stop_loss is not None and self.entry_price <= self.stop_loss:
            raise ValueError("Stop loss must be less than to entry price.")
        if self.take_profit is not None and self.entry_price >= self.take_profit:
            raise ValueError("Take profit must be greater than to entry price.")

