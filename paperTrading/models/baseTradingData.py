from dataclasses import dataclass, field, replace
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID, uuid4

from paperTrading.enums import PositionDirection, OrderAction, OrderType


@dataclass
class BaseTradingData:
    confidence: float

    direction: PositionDirection
    action: OrderAction
    type: OrderType = field(default=None, init=False)

    entry_price: Optional[float] = None
    qty: Optional[float] = None

    symbol: Optional[str] = None
    creation_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    max_holding_period: Optional[timedelta] = None

    uuid: UUID = field(default_factory=uuid4, init=False)
    root_uuid: UUID = field(default_factory=uuid4)

    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    is_maker: bool = field(default=False)
    commission: float = 0

    def __post_init__(self):
        if self.entry_price is not None and self.entry_price <= 0:
            raise ValueError("Entry price must be greater than 0")
        if self.qty is not None and self.qty <= 0:
            raise ValueError("Quantity must be greater than 0")
        if self.stop_loss is not None and self.stop_loss <= 0:
            raise ValueError("Stop loss must be greater than 0")
        if self.take_profit is not None and self.take_profit <= 0:
            raise ValueError("Take profit must be greater than 0")
        if self.max_holding_period is not None and self.max_holding_period <= timedelta(0):
            raise ValueError("Max holding period must be greater than 0")
        if self.type == OrderType.LIMIT and self.entry_price is None:
            raise ValueError("Limit order must have entry price")


    def pnl(self, closed_at_price: float) -> float:
        if self.direction == PositionDirection.LONG:
            return (closed_at_price - self.entry_price) * self.qty
        else:
            return (self.entry_price - closed_at_price) * self.qty

    def copy(self):
        """
        Returns a copy of the object with its unique uuid
        :return: self
        """
        copied = replace(self)
        copied.uuid = uuid4()
        return copied