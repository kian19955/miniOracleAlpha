from typing import Optional
from dataclasses import dataclass


@dataclass
class BaseGenome:
    name: str

    mutate_probability: Optional[float] = None
    mate_probability: Optional[float] = None

    mutate_operator: Optional[...] = None
    mate_operator: Optional[...] = None

    type_value: any = None

    def __post_init__(self):
        if self.mutate_probability is None or not (0 <= self.mutate_probability <= 1):
            raise ValueError("mutate_probability must be between 0 and 1")
        if self.mate_probability is None or not (0 <= self.mate_probability <= 1):
            raise ValueError("mate_probability must be between 0 and 1")

    def create(self, *args, **kwargs) -> any:
        return self.type_value