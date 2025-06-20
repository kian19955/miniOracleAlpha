from datetime import datetime

from paperTrading.reporters import ReportContext
from paperTrading.reporters.baseReporter import BaseReporter


class ConsoleReporter(BaseReporter):
    def __init__(self, *args, str_end: str = "\n", **kwargs):
        super().__init__(*args, **kwargs)
        self.last_networth = None
        self.datetime_start = None
        self.str_end = str_end

    def start(self):
        self.datetime_start: datetime = datetime.now()
        self.last_networth = self.portfolio.balance

    def report(self, ctx: ReportContext):
        net_worth = round(self.portfolio.net_worth(self.simulator.df.iloc[-1]["Close"]), 4)
        conf = ctx.latest_request if isinstance(ctx.latest_request, (float, int)) else ctx.latest_request.confidence

        print(
            f"DELTA: {datetime.now() - self.datetime_start} | "
            f"OR: {len(self.portfolio.order_requests)} | "
            f"POS: {len(self.portfolio.positions)} | "
            f"TR: {len(self.portfolio.trade_records)} | "
            f"NETWORTH: {net_worth} {"(+)" if net_worth >= self.last_networth else ""}{round(net_worth - self.last_networth, 2)} | "
            f"CONF: {conf} | "
            f"PRICE: {self.simulator.df.iloc[-1]['Close']}", end=self.str_end
        )

        self.last_networth = net_worth