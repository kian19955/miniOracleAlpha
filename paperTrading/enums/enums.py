from enum import Enum


class Side(Enum):
    LONG = "long"
    SHORT = "short"

class Action(Enum):
    CLOSE = "close"
    OPEN = "buy"