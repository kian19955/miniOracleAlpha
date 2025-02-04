import random
from typing import Optional

from .baseGenome import BaseGenome

class BoolGenome(BaseGenome):
    def __init__(self, name: str, mutate_probability: Optional[float] = None, mate_probability: Optional[float] = None):
        super().__init__(name, mutate_probability, mate_probability)

    @staticmethod
    def create():
        return random.choice([True, False])