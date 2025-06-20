from paperTrading.models import Portfolio
from paperTrading.reporters import ReportContext


class BaseReporter:
    def __init__(self, portfolio: Portfolio, simulator: 'PaperTrader') -> None:
        self.portfolio = portfolio
        self.simulator = simulator

    def start(self):
        """Will be called at the start of the simulation"""
        pass

    def report(self, ctx: ReportContext):
        """Will be called at each iteration of the simulation"""
        pass

    def end(self):
        """Will be called at the end of the simulation"""
        pass
