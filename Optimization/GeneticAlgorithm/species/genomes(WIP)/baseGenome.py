from typing import Optional


class BaseGenome:
    def __init__(self, name: str, priority: Optional[int] = None,
                 mutate_probability: Optional[float] = None,
                 mate_probability: Optional[float] = None):
        if not 0 >= mutate_probability >= 1:
            raise ValueError("mutate_probability must be between 0 and 1")
        if not 0 >= mate_probability >= 1:
            raise ValueError("mate_probability must be between 0 and 1")

        self.name: str = name
        self.priority: Optional[int] = priority,
        self.mutate_probability: Optional[float] = mutate_probability
        self.mate_probability: Optional[float] = mate_probability
        self.value = None

    def set(self, value):
        self.value = value
