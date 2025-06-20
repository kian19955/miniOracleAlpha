from dataclasses import dataclass, field
from typing import Optional, Callable
from uuid import UUID
import copy
import csv

from paperTrading.models import TradeRecord, Position, OrderRequest
import logging

logger = logging.getLogger("oracle.analysis")



@dataclass
class Portfolio:
    """
    A class representing a user's trading portfolio, containing order requests,
    open positions, and closed trade records.

    :param balance: Initial balance of the portfolio.
    :param allow_dept: Whether to allow positions that exceed the available balance.
    :param on_order_request_added: List of callbacks triggered when an order request is added.
    :param on_position_added: List of callbacks triggered when a position is added.
    :param on_trade_record_added: List of callbacks triggered when a trade record is added.
    :param order_requests: List of current order requests.
    :param positions: List of current open positions.
    :param trade_records: List of closed trade records.
    """
    balance: float

    allow_dept: bool = False

    on_order_request_added: list[Callable[[OrderRequest], None]] = field(default_factory=list)
    on_position_added: list[Callable[[Position], None]] = field(default_factory=list)
    on_trade_record_added: list[Callable[[TradeRecord], None]] = field(default_factory=list)

    order_requests: list[OrderRequest] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    trade_records: list[TradeRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.balance < 0:
            raise ValueError("Initial balance must be non-negative")

    def add_order_request(self, order_request: OrderRequest) -> None:
        """
        Add a new order request to the portfolio.

        :param order_request: The OrderRequest instance to add.
        """
        self.order_requests.append(order_request)

        for callback in self.on_order_request_added:
            callback(order_request)

    def rmv_order_request(self, uuid: UUID) -> None:
        """
        Remove an order request from the portfolio by its UUID.

        :param uuid: The UUID of the order request to remove.
        """
        self.order_requests[:] = [o for o in self.order_requests if o.uuid != uuid]

    def add_position(self, position: Position) -> None:
        """
        Add a new position to the portfolio. If it originated from an order request,
        the corresponding request is removed.

        :param position: The Position instance to add.
        """
        cost: float = position.entry_price * position.qty
        if not self.allow_dept and cost > self.balance:
            raise ValueError("Not enough balance")

        self.balance -= cost
        self.rmv_order_request(position.uuid)
        self.positions.append(position)

        for callback in self.on_position_added:
            callback(position)

    def close_position(
        self,
        uuid: UUID,
        closed_at_price: Optional[float] = None,
        trade_record: Optional[TradeRecord] = None
    ) -> None:
        """
        Close an open position by UUID and record the trade.

        :param uuid: The UUID of the position to close.
        :param closed_at_price: Price at which the position is closed. Required if `trade_record` is not provided.
        :param trade_record: A TradeRecord to use. If None, one will be created from the position.
        :raises ValueError: If neither `closed_at_price` nor `trade_record` is provided.
        """
        if trade_record is None and closed_at_price is None:
            raise ValueError("Either trade_record or closed_at_price must be provided")

        for pos in self.positions:
            if pos.uuid == uuid:
                record = trade_record or TradeRecord.from_position(pos, closed_at_price=closed_at_price)

                self.balance += record.total_value()
                self.positions.remove(pos)
                self.trade_records.append(record)

                for callback in self.on_trade_record_added:
                    callback(record)

                return

    @staticmethod
    def find_by_attributes(
        objects: list[OrderRequest | Position | TradeRecord],
        return_copy: bool = True,
        **filters
    ) -> list[OrderRequest | Position | TradeRecord]:
        """
        Find and return a list of portfolio objects that match all given attribute filters.

        :param objects: A list of OrderRequest, Position, or TradeRecord instances.
        :param return_copy: If True, return copies of matched objects; else, return originals.
        :param filters: Attribute-value pairs to match on.
        :return: A list of matched objects.
        :raises AttributeError: If an attribute doesn't exist on an object.
        """
        results = []

        for item in objects:
            if all(getattr(item, key) == value for key, value in filters.items()):
                results.append(copy.copy(item) if return_copy else item)

        return results


    def get_qty(self, symbol: Optional[str] = None) -> float:
        """
        Return the total quantity of positions in the portfolio.

        :param symbol: Filter by symbol
        :return: Total quantity
        """
        return sum(pos.qty for pos in self.positions if pos.symbol == symbol or symbol is None)

    def net_worth(self, latest_price: float) -> float:
        """
        Calculate the net worth of the portfolio.
        :return:
        """
        net_worth = self.balance
        for pos in self.positions:
            net_worth += pos.total_value(latest_price)

        return net_worth

    @property
    def realized_pnl(self) -> float:
        """
        Calculate the total profit/loss across all trade records.
        :return:
        """
        return sum(tr.pnl for tr in self.trade_records)

    def save_to_csv(self, path: str) -> None:
        """
        Save all trade records to an CSV file.

        :param path: The destination file path.
        """
        if len(self.trade_records) == 0:
            return

        data = []
        for trade_record in self.trade_records:
            data.append(trade_record.to_dict_for_csv())

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    def __repr__(self) -> str:
        return (
            f"Portfolio(balance={self.balance}, "
            f"order_requests={self.order_requests}, "
            f"positions={self.positions}, "
            f"trade_records={self.trade_records})"
        )
