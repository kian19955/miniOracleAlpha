from random import choice, uniform
from enum import EnumMeta
from typing import Optional

from .baseGenome import BaseGenome


class EnumGenome(BaseGenome):
    def __init__(
            self,
            name: str,
            enum_settings: Optional[dict[str, float]] = None,
            enum_class: Optional[EnumMeta] = None,
            mutate_probability: Optional[float] = None,
            mate_probability: Optional[float] = None
    ):
        super().__init__(name, mutate_probability, mate_probability)
        self.enum_class = enum_class
        self.enum_settings = enum_settings

    def retrieve_random_enum(self):
        try:
            roll = uniform(0, sum(self.enum_settings.values()))

            for enum_value, prob in self.enum_settings.items():
                roll -= prob
                if roll <= 0:
                    return enum_value

        except KeyError:
            return choice(list(self.enum_class))

    def create(self):
        return self.retrieve_random_enum()
