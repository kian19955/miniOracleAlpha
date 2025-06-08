from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from paperTrading.enums import Side, Action


@dataclass
class BaseTradingData:
    symbol: str

    confidence: float

    entry_price: Optional[float]
    side: Side
    action: Action
    qty: Optional[float]

    timestamp: float = field(default_factory=datetime.now(timezone.utc).timestamp)

    uuid: UUID = field(default_factory=uuid4, init=False)
    root_uuid: UUID = field(default_factory=uuid4)

    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def return_timestamp(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)