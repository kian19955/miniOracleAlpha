from typing import Optional

from .baseGenome import BaseGenome


class EnumGenome(BaseGenome):
    def __init__(
            self,
            name: str,
            enum_settings: Optional[dict[str, float]] = None,
            priority: Optional[int] = None,
            mutate_probability: Optional[float] = None,
            mate_probability: Optional[float] = None
    ):
        super().__init__(name, priority, mutate_probability, mate_probability)
        self.enum_settings = enum_settings
