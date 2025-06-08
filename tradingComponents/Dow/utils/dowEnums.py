from enum import Enum

class Trend(Enum):
    UPTREND = "Uptrend"
    DOWNTREND = "Downtrend"
    SIDEWAYS = "Sideways"

class Phase(Enum):
    ACCUMULATION = 'Accumulation Phase'
    PARTICIPATION = 'Participation Phase'
    DISTRIBUTION = 'Distribution Phase'
    MARKDOWN = 'Markdown Phase'
    CONSOLIDATION_INCREASED_VOLATILITY = 'Consolidation - Increased Volatility'
    CONSOLIDATION_DECREASED_VOLATILITY = 'Consolidation - Decreased Volatility'
