from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from paperTrading.enums import Side, Action


@dataclass
class BaseTradingData:
    confidence: float

    side: Side
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
        if self.side == Side.LONG:
            return (closed_at_price - self.entry_price) * self.qty
        else:
            return (self.entry_price - closed_at_price) * self.qty

    def return_timestamp(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)