from typing import Optional

from .baseGenome import BaseGenome

class UnionGenome(BaseGenome):
    def __init__(self, name: str, genomes: Optional[list[BaseGenome]] = None):
        super().__init__(name)
        self._genomes = genomes or []

    @property
    def genome_args(self):
        return self._genomes

    def add(self, genome: BaseGenome):
        self._genomes.append(genome)

    def rmv(self, genome: BaseGenome):
        self._genomes.remove(genome)