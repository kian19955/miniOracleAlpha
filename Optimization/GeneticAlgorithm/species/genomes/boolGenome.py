import random
from dataclasses import dataclass

from .baseGenome import BaseGenome

@dataclass
class BoolGenome(BaseGenome):
    def create(self, *args, **kwargs) -> bool:
        return random.choice([True, False])