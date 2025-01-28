from random import gauss
from typing import Optional

def gauss_clamp(
        current: float | int,
        start: float | int,
        stop: float | int,
        step: Optional[float | int] = None,
        strength: float = 0.1,
        is_int: bool = False
) -> float | int:
    """
    Applies Gaussian noise to a value, aligns it to the nearest step,
    and clamps it within a range.

    :param current: Value to mutate.
    :param start: Minimum bound for clamping.
    :param stop: Maximum bound for clamping.
    :param step: Step size for rounding.
    :param strength: Noise strength as a fraction of (stop - start). Default is 0.1.
    :param is_int: If True, return as an integer. Default is False.

    :return: Mutated value rounded to the nearest step and clamped.

    :raises ValueError: If start is greater than stop or step is non-positive.
    :raises ValueError: If step is non-positive.
    """
    if start > stop:
        raise ValueError("start must be less than or equal to stop")
    if step is not None and step <= 0:
        raise ValueError("step must be positive")

    std_dev = (stop - start) * strength
    mutated: float = current + gauss(0, std_dev)

    if is_int:
        step = int(step) if step is not None else 1
        mutated = round(mutated / step) * step

    else:
        decimals: int = len(str(step).split('.')[1]) if '.' in str(step) else 0
        if step is not None:
            mutated = round(mutated / step, decimals) * step
        else:
            mutated = round(mutated, decimals)

    return max(min(mutated, stop), start)
