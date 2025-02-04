from typing import Optional, Union
from random import randrange

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


class NumericGenome(BaseGenome):
    def __init__(self,
                 name: str,
                 start: Union[float, int, str],
                 stop: Union[float, int, str],
                 step: Optional[Union[float, int, str]] = None,
                 genome_type: type = int,
                 mutate_probability: float = 0.1,
                 mate_probability: float = 0.5):
        # If start and stop are numbers, enforce start < stop.
        if isinstance(start, (int, float)) and isinstance(stop, (int, float)):
            if start >= stop:
                raise ValueError("start must be less than stop")
        super().__init__(name, mutate_probability, mate_probability)
        self.start = start
        self.stop = stop
        self.step = step
        self.type = genome_type

    def resolve_genome(self, individual) -> tuple[float, float, float]:
        start = self.start
        stop = self.stop
        step = self.step

        if isinstance(self.start, str):
            start = eval(self.start, SAFE_GLOBALS, dict(individual, **SAFE_BUILTINS))
        if isinstance(self.stop, str):
            stop = eval(self.stop, SAFE_GLOBALS, dict(individual, **SAFE_BUILTINS))
        if isinstance(self.step, str):
            step = eval(self.step, SAFE_GLOBALS, dict(individual, **SAFE_BUILTINS))

        return start, stop, step

    def create(self, individual):
        if self.type is int:
            return randrange(
                *self.resolve_genome(individual)
            )

        return randfloat(
            *self.resolve_genome(individual)
        )
