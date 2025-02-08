from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import random

from .baseGenome import BaseGenome


@dataclass
class EnumGenome(BaseGenome):
    enum_class: Optional[type[Enum]] = None
    enum_settings: dict[Enum, float] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        if self.enum_class and not issubclass(self.enum_class, Enum):
            raise ValueError(f"{self.enum_class} is not a subclass of Enum")

    def retrieve_random_enum(self) -> Enum:
        """Selects a random enum value based on the given probability distribution."""
        if not self.enum_settings and self.enum_class:
            return random.choice(list(self.enum_class))  # Randomly choose if no probabilities are set.

        total_weight = sum(self.enum_settings.values())
        if total_weight == 0:
            raise ValueError("Total weight of enum probabilities cannot be zero.")

        roll = random.uniform(0, total_weight)
        for enum_value, prob in self.enum_settings.items():
            roll -= prob
            if roll <= 0:
                return enum_value

        raise ValueError("Failed to select a valid enum value.")

    def create(self) -> Enum:
        return self.retrieve_random_enum()
