from dataclasses import dataclass

from paperTrading.models import OrderRequest


class ContextBuilder:
    def __init__(self, has_reporter: bool = True):
        self.has_reporter = has_reporter
        self._context = {}

    def set_latest_request(self, latest_request: float | OrderRequest | None):
        if not self.has_reporter:
            return
        self._context["latest_request"] = latest_request

    def build(self):
        return ReportContext(**self._context)

    def reset(self):
        self._context = {}


@dataclass(frozen=True)
class ReportContext:
    latest_request: float | OrderRequest | None

