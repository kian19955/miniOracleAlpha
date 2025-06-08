from dataclasses import dataclass

from paperTrading.models import BaseTradingData

@dataclass
class Position(BaseTradingData):
    """
    :param uuid: universally unique identifier (uuid.uuid4())
    :param symbol: e.g. "BTCUSDT"
    :param timestamp: unix timestamp at which the asset was bought, timezone is UTC

    :param confidence: confidence level of the OrderRequest (-1.0 to 1.0) where -1 = max sell, 0 = neutral, +1 = max buy

    :param entry_price: price at which the asset was bought
    :param side: Side.LONG or Side.SHORT
    :param action: Action.SELL or Action.BUY
    :param qty: quantity of the asset

    :param stop_loss: the price where the stop loss is placed
    :param take_profit: the price where the take profit is placed
    """

    def __post_init__(self):
        if self.stop_loss is not None and self.entry_price <= self.stop_loss:
            raise ValueError("Stop loss must be less than to entry price.")
        if self.take_profit is not None and self.entry_price >= self.take_profit:
            raise ValueError("Take profit must be greater than to entry price.")

    @classmethod
    def from_order_request(cls, order_request: 'OrderRequest') -> 'Position':
        return Position(
            root_uuid=order_request.root_uuid,
            symbol=order_request.symbol,
            timestamp=order_request.timestamp,
            confidence=order_request.confidence,
            entry_price=order_request.entry_price,
            side=order_request.side,
            action=order_request.action,
            qty=order_request.qty,
            stop_loss=order_request.stop_loss,
            take_profit=order_request.take_profit
        )