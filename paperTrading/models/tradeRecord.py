from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from xml.dom.minidom import Element
from xml.etree.ElementTree import SubElement

from paperTrading.enums import Side
from paperTrading.models import Position
from paperTrading.models import BaseTradingData

@dataclass(kw_only=True)
class TradeRecord(BaseTradingData):
    """
    :param uuid: universally unique identifier (uuid.uuid4())
    :param symbol: e.g. "BTCUSDT"
    :param entry_timestamp: unix timestamp at which the asset was bought, timezone is UTC
    :param exit_timestamp: unix timestamp at which the asset was sold, timezone is UTC

    :param confidence: confidence level (-1.0 to 1.0) where -1 = max sell, 0 = neutral, +1 = max buy

    :param entry_price: price at which the asset was bought
    :param side: Side.LONG or Side.SHORT
    :param action: Action.SELL or Action.BUY
    :param qty: quantity in base units, if none the Simulator will decide

    :param pnl: profit/loss in quote currency

    :param stop_loss: stop loss if used
    :param take_profit: take profit if used
    """
    entry_timestamp: float
    exit_timestamp: float

    pnl: float

    @classmethod
    def from_position(cls, position: Position, pnl: Optional[float] = None, closed_at_price: Optional[float] = None) -> "TradeRecord":
        """
        Creates a TradeRecord from a Position

        :param position: A Position
        :param pnl: If None will be calculated from closed_at_price
        :param closed_at_price: Price at which the asset was sold
        :return: A TradeRecord object
        """
        if pnl is None and closed_at_price is None:
            raise ValueError("Either pnl or closed_at_price must be provided")

        if pnl is None:
            if position.side == Side.LONG:
                pnl = (closed_at_price - position.entry_price) * position.qty
            else:
                pnl = (position.entry_price - closed_at_price) * position.qty

        return cls(
            root_uuid=position.root_uuid,

            symbol=position.symbol,
            entry_timestamp=position.timestamp,
            exit_timestamp=datetime.now().timestamp(),

            confidence=position.confidence,

            entry_price=position.entry_price,
            side=position.side,
            action=position.action,
            qty=position.qty,

            pnl=pnl,

            stop_loss=position.stop_loss,
            take_profit=position.take_profit
        )

    def save_to_xml(self, root: Element) -> None:
        trade_record_element = SubElement(root, "trade_record", {"uuid": str(self.uuid)})

        # Basic Fields
        SubElement(trade_record_element, "symbol").text = self.symbol

        SubElement(trade_record_element, "confidence").text = str(self.confidence)

        SubElement(trade_record_element, "entry_price").text = str(self.entry_price)
        SubElement(trade_record_element, "side").text = self.side.name
        SubElement(trade_record_element, "action").text = self.action.name
        SubElement(trade_record_element, "qty").text = str(self.qty)
        SubElement(trade_record_element, "pnl").text = str(self.pnl)

        # Timestamps, converting to ISO format for readability
        entry_ts = datetime.fromtimestamp(self.entry_timestamp, tz=timezone.utc).isoformat()
        exit_ts = datetime.fromtimestamp(self.exit_timestamp, tz=timezone.utc).isoformat()
        SubElement(trade_record_element, "entry_timestamp").text = entry_ts
        SubElement(trade_record_element, "exit_timestamp").text = exit_ts

        if self.stop_loss is not None:
            SubElement(trade_record_element, "stop_loss").text = str(self.stop_loss)
        if self.take_profit is not None:
            SubElement(trade_record_element, "take_profit").text = str(self.take_profit)