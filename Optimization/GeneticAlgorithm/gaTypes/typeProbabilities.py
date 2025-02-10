from dataclasses import dataclass

@dataclass
class MateTypeProbabilities:
    MATING_PROP: float = 0.9,
    FLOAT: float = 0.5,
    INT: float = 0.5,
    BOOL: float = 0.5
    ENUM: float = 0.5,
    UNION: float = 0.5,
    OTHER: float = 0.5


@dataclass
class MutateTypeProbabilities:
    FLOAT: float = 0.1,
    INT: float = 0.1,
    BOOL: float = 0.1,
    ENUM: float = 0.1,
    UNION: float = 0.1,
    OTHER: float = 0.1
