from enum import Enum


class OrderType(Enum):
    LONG = "long"
    SHORT = "short"

class Action(Enum):
    CLOSE = "close"
    OPEN = "open"