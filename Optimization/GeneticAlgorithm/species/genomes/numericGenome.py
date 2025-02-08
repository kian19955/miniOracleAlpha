from typing import Optional
from random import randrange
from dataclasses import dataclass

from oracleMaths import randfloat
from .baseGenome import BaseGenome

SAFE_BUILTINS = {
    'abs': abs,
    'min': min,
    'max': max,
    'sum': sum,
    'pow': pow,
    'len': len,
    'round': round,
}
SAFE_GLOBALS = {
    '__builtins__': SAFE_BUILTINS
}


@dataclass
class NumericGenome(BaseGenome):
    start: float | int | str = 0
    stop: float | int | str = 100
    step: Optional[float | int | str] = 1
    genome_type: type = int

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.start, (int, float)) and isinstance(self.stop, (int, float)):
            if self.start >= self.stop:
                raise ValueError("start must be less than stop")

    def resolve_genome(self, individual: dict) -> tuple[float, float, float]:
        s = self.start
        st = self.stop
        sp = self.step
        if isinstance(self.start, str):
            s = eval(self.start, SAFE_GLOBALS, dict(individual, **SAFE_BUILTINS))
        if isinstance(self.stop, str):
            st = eval(self.stop, SAFE_GLOBALS, dict(individual, **SAFE_BUILTINS))
        if self.step is not None and isinstance(self.step, str):
            sp = eval(self.step, SAFE_GLOBALS, dict(individual, **SAFE_BUILTINS))
        return s, st, sp

    def create(self, individual: dict) -> float | int:
        s, st, sp = self.resolve_genome(individual)
        if self.genome_type is int:
            return randrange(int(s), int(st), int(sp) if sp is not None else 1)
        else:
            return randfloat(s, st, sp)