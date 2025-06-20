from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from paperTrading.enums import OrderType, Action


@dataclass
class BaseTradingData:
    confidence: float

    type: OrderType
    action: Action
    entry_price: Optional[float] = None
    qty: Optional[float] = None

    symbol: Optional[str] = None
    timestamp: float = field(default_factory=datetime.now(timezone.utc).timestamp)

    uuid: UUID = field(default_factory=uuid4, init=False)
    root_uuid: UUID = field(default_factory=uuid4)

    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def pnl(self, closed_at_price: float) -> float:
        if self.type == OrderType.LONG:
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

    def return_timestamp(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)