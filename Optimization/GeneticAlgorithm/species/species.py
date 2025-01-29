from .genomes import BaseGenome


class Species:
    def __init__(self):
        self._genomes: dict[str, BaseGenome] = {}

    def add_genome(self, genome: BaseGenome | list[BaseGenome]):
        if not isinstance(genome, list):
            genome = [genome]

        for g in genome:
            self._genomes[g.name] = g

    def remove_genomes(self, genome: BaseGenome | list[BaseGenome]):
        if not isinstance(genome, list):
            genome = [genome]

        for g in genome:
            del self._genomes[g.name]

    def get(self, name: str):
        return self._genomes[name]