from typing import Optional

from .baseGenome import BaseGenome

class NumericGenome(BaseGenome):
    def __init__(
            self,
            name: str,
            start: float | int | str,
            stop: float | int | str,
            step: Optional[float | int | str] = None,
            genome_type: type[int | float] = int,
            mutate_probability: Optional[float] = None,
            mate_probability: Optional[float] = None,
            priority: Optional[int] = None,
    ):
        if start >= stop:
            raise ValueError("start must be less than stop")

        super().__init__(name, priority, mutate_probability, mate_probability)
        self.start = start
        self.stop = stop
        self.step = step
        self.type = genome_type

    def resolve_genome(self, context):
        if isinstance(self.start, str):
            start = eval(self.start, **context)
        else:
            start = self.start

        if isinstance(self.stop, str):
            stop = eval(self.start, **context)
        else:
            stop = self.stop

        if isinstance(self.step, str):
            step = eval(self.start, **context)
        else:
            step = self.step

        return start, stop, step