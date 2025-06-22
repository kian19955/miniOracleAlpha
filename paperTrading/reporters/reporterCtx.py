from dataclasses import dataclass, field
from functools import wraps
from typing import Optional
from uuid import UUID

from paperTrading.models import OrderRequest, Position, TradeRecord


@dataclass
class MutableReportContext:
    latest_request: Optional[float | OrderRequest] = None

    dropped_order_requests: list[UUID] = field(default_factory=list)
    new_order_requests: list[UUID] = field(default_factory=list)
    new_positions: list[UUID] = field(default_factory=list)
    new_trade_records: list[UUID] = field(default_factory=list)

@dataclass(frozen=True)
class ReportContext:
    latest_request: Optional[float | OrderRequest]

    dropped_order_requests: tuple[UUID, ...]
    new_order_requests: tuple[UUID, ...]
    new_positions: tuple[UUID, ...]
    new_trade_records: tuple[UUID, ...]

class ContextBuilder:
    def __init__(self, has_reporter: bool = True):
        self.has_reporter = has_reporter
        self._context = MutableReportContext()

    @staticmethod
    def only_if_reporter(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.has_reporter:
                return func(self, *args, **kwargs)

        return wrapper

    @only_if_reporter
    def set_latest_request(self, latest_request: Optional[float | OrderRequest]):
        self._context.latest_request = latest_request

    @only_if_reporter
    def add_dropped_order_request(self, uuid: UUID):
        self._context.dropped_order_requests.append(uuid)

    @only_if_reporter
    def add_new_order_request(self, uuid: UUID):
        self._context.new_order_requests.append(uuid)

    @only_if_reporter
    def add_new_position(self, uuid: UUID):
        self._context.new_positions.append(uuid)

    @only_if_reporter
    def add_new_trade_record(self, uuid: UUID):
        self._context.new_trade_records.append(uuid)

    def build(self) -> ReportContext:
        return ReportContext(
            latest_request=self._context.latest_request,
            dropped_order_requests=tuple(self._context.dropped_order_requests),
            new_order_requests=tuple(self._context.new_order_requests),
            new_positions=tuple(self._context.new_positions),
            new_trade_records=tuple(self._context.new_trade_records),
        )

    def reset(self):
        self._context = MutableReportContext()
