import copy
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID
from xml.dom.minidom import Element
from xml.etree.ElementTree import ElementTree

from paperTrading.models import TradeRecord, Position, OrderRequest


@dataclass
class Portfolio:
    balance: float
    order_requests: list[OrderRequest] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    trade_records: list[TradeRecord] = field(default_factory=list)

    def __post_init__(self):
        if self.balance < 0:
            raise ValueError("Initial balance must be non-negative")

    def add_order_request(self, order_request: OrderRequest) -> None:
        self.order_requests.append(order_request)

    def rmv_order_request(self, uuid: UUID) -> None:
        for ord_req in self.order_requests:
            if ord_req.uuid == uuid:
                self.order_requests.remove(ord_req)

    def add_position(self, position) -> None:
        """
        Add a position to the portfolio, and remove it from the order requests if it exists

        :param position: The position to add
        """
        for ord_req in self.order_requests:
            if ord_req.uuid == position.uuid:
                self.order_requests.remove(ord_req)

        self.positions.append(position)

    def close_position(
            self,
            uuid: UUID,
            closed_at_price: Optional[float] = None,
            trade_record: Optional[TradeRecord] = None
    ) -> None:
        """
        Close a position and create a trade record either by creating a trade record or by being passed one
        :param uuid: The UUID of the position
        :param closed_at_price: The price at which the asset was sold, must be provided if trade_record is not
        :param trade_record: The trade record, if not provided it will be created using the closed_at_price
        :raises ValueError: If neither trade_record nor closed_at_price is provided
        """
        if trade_record is None and closed_at_price is None:
            raise ValueError("Either trade_record or closed_at_price must be provided")

        for pos in self.positions:
            if pos.uuid == uuid:
                tr = trade_record or TradeRecord.from_position(pos, closed_at_price=closed_at_price)
                self.balance += tr.pnl

                self.trade_records.append(tr)
                self.positions.remove(pos)
                return

    @staticmethod
    def find_by_attributes(
            objects: list[OrderRequest | Position | TradeRecord],
            return_copy: bool = True,
            **filters
    ) -> list[OrderRequest | Position | TradeRecord]:
        """
        Find objects by their attributes

        :param objects: pass the portfolios object. example: objects = portfolio.positions
        :param return_copy: If True, return a copy of the object
        :param filters: Key value pairs which the object must have

        :return: A list of objects that match

        :raise AttributeError: If the key is not an attribute of the object
        """
        result = []

        for item in objects:
            if all(getattr(item, key) == value for key, value in filters.items()):
                result.append(copy.copy(item) if return_copy else item)
        return result

    def save_to_xml(self, path: str) -> None:
        root = Element(f"trade_records")

        for trade_record in self.trade_records:
            trade_record.save_to_xml(root)

        tree = ElementTree(root)
        tree.write(path, encoding="utf-8", xml_declaration=True)
