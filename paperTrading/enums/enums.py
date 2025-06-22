from enum import Enum


class PositionDirection(Enum):
    LONG = "long"
    SHORT = "short"

class OrderAction(Enum):
    CLOSE = "close_pos"
    OPEN = "open_pos"

class OrderType(Enum):
    LIMIT = "limit"
    MARKET = "market"