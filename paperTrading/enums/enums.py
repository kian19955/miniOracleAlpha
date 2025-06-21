from enum import Enum


class OrderType(Enum):
    LONG = "long"
    SHORT = "short"

class Action(Enum):
    CLOSE = "close_pos"
    OPEN = "open_pos"