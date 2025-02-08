from random import choice
from dataclasses import dataclass, field

from . import NumericGenome
from .baseGenome import BaseGenome

@dataclass
class UnionGenome(BaseGenome):
    genomes: list[BaseGenome] = field(default_factory=list)

    @property
    def genome_args(self) -> list[BaseGenome]:
        return self.genomes

    def add(self, genome: BaseGenome) -> None:
        self.genomes.append(genome)

    def rmv(self, genome: BaseGenome) -> None:
        self.genomes.remove(genome)

    def create(self, ctx: dict = None) -> BaseGenome:
        chosen = choice(self.genomes)
        if isinstance(chosen, NumericGenome):
            chosen = chosen.create(ctx)
        else:
            chosen = chosen.create()
        return chosen