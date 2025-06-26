from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from xml.dom.minidom import Element
from xml.etree.ElementTree import SubElement

from paperTrading.enums import PositionDirection
from paperTrading.models import Position
from paperTrading.models import BaseTradingData

@dataclass(kw_only=True)
class TradeRecord(BaseTradingData):
    """
    :param uuid: universally unique identifier (uuid.uuid4())
    :param symbol: e.g. "BTCUSDT"
    :param entry_time: unix timestamp at which the asset was bought, timezone is UTC
    :param exit_time: unix timestamp at which the asset was sold, timezone is UTC

    :param confidence: confidence level (-1.0 to 1.0) where -1 = max sell, 0 = neutral, +1 = max buy

    :param entry_price: price at which the asset was bought
    :param direction: Side.LONG or Side.SHORT
    :param action: Action.SELL or Action.BUY
    :param qty: quantity in base units, if none the Simulator will decide

    :param pnl: profit/loss in quote currency

    :param stop_loss: stop loss if used
    :param take_profit: take profit if used
    """
    closing_reason: str

    entry_time: datetime
    exit_time: datetime

    pnl: float

    @classmethod
    def from_position(
            cls,
            position: Position,
            pnl: Optional[float] = None,
            closed_at_price: Optional[float] = None,
            closing_reason: Optional[str] = None
    ) -> "TradeRecord":
        """
        Creates a TradeRecord from a Position

        :param closing_reason: The reason the position was closed
        :param position: A Position
        :param pnl: If None will be calculated from closed_at_price
        :param closed_at_price: Price at which the asset was sold
        :return: A TradeRecord object
        """
        if pnl is None and closed_at_price is None:
            raise ValueError("Either pnl or closed_at_price must be provided")

        if pnl is None:
            pnl = position.pnl(closed_at_price)

        return cls(
            root_uuid=position.root_uuid,

            symbol=position.symbol,

            entry_time=position.creation_time,
            exit_time=datetime.now(timezone.utc),
            max_holding_period=position.max_holding_period,

            confidence=position.confidence,
            closing_reason=closing_reason,

            entry_price=position.entry_price,
            direction=position.direction,
            action=position.action,
            qty=position.qty,

            pnl=pnl,

            stop_loss=position.stop_loss,
            take_profit=position.take_profit,

            commission=position.commission
        )

    def total_value(self) -> float:
        return (self.entry_price * self.qty) + self.pnl

    def to_dict_for_csv(self) -> dict[str, str]:
        return {
            "uuid": self.uuid,
            "root_uuid": self.root_uuid,

            "symbol": self.symbol,

            "confidence": self.confidence,
            "closing_reason": self.closing_reason,

            "side": self.direction.name,
            "action": self.action.name,
            "qty": self.qty,
            "pnl": self.pnl,

            "entry_price": self.entry_price,
            "entry_timestamp": str(self.entry_time),
            "exit_timestamp": str(self.exit_time),
            "holding_duration": str(self.max_holding_period),

            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,

            "is_maker": self.is_maker,
            "commission": self.commission
        }