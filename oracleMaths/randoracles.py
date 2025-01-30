from random import uniform, randint
from typing import Optional

def randfloat(start: float, stop: float, step: Optional[float] = None) -> float:
    if step is None:
        return uniform(start, stop)
    else:
        count = int((stop - start) / step)
        return randint(0, count) * step + start