import random
from enum import EnumMeta
from inspect import signature
from types import MappingProxyType
from collections import defaultdict, OrderedDict
from typing import Optional, get_origin, Union, get_args

from .genomes import BaseGenome, BoolGenome, EnumGenome, NumericGenome, UnionGenome

import re

import logging

logger = logging.getLogger("oracle.analysis")

class Species:
    def __init__(self):
        self._genomes: dict[str, BaseGenome] = OrderedDict()
        self.market_genomes: dict[str, BaseGenome] = {}

    @staticmethod
    def _extract_relation(operation: str) -> tuple[list[str], str]:
        """
        Extract dependency placeholders in the form '{{param}}' from the given operation
        and return a list of dependency names along with a parsed version of the operation.
        """
        relations = re.findall(r'\{\{([^}]+)}}', operation)
        parsed_operation = re.sub(r"\{\{|}}", "", operation)
        return relations, parsed_operation

    def _build_dependency_graph(self) -> dict[str, list[str]]:
        """
        Iterate over the genomes. For each genome that defines start/stop/step as strings,
        extract dependencies (placeholders) and build a graph.
        """
        graph = defaultdict(list)
        for param_name, genome in self._genomes.items():
            if (isinstance(genome, UnionGenome) and not NumericGenome in genome._genomes) or not isinstance(genome, NumericGenome):
                continue
            elif isinstance(genome, UnionGenome):
                genomes = [g for g in genome._genomes if isinstance(g, NumericGenome)]
            else:
                genomes = [genome]

            for g in genomes:
                dependencies = []

                for key in ['start', 'stop', 'step']:
                    value = getattr(genome, key, None)

                    if isinstance(value, str):
                        rels, parsed_operation = self._extract_relation(value)
                        setattr(genome, key, parsed_operation)
                        dependencies.extend(rels)

                for dep in dependencies:
                    graph[dep].append(param_name)

        return graph

    def _topological_sort(self, graph: dict[str, list[str]]) -> OrderedDict[str, BaseGenome]:
        """
        Perform a topological sort on the dependency graph.
        param_types is a dict mapping parameter names to their type annotations.
        """
        # Initialize in-degree for each parameter.
        in_degree = {param: 0 for param in self._genomes}
        for deps in graph.values():
            for param in deps:
                in_degree[param] += 1

        # Start with all parameters that have no incoming edges.
        queue = [param for param, degree in in_degree.items() if degree == 0]
        ordered = OrderedDict()
        while queue:
            param = queue.pop(0)
            ordered[param] = self._genomes[param]

            for dependent in graph[param]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(ordered) != len(self._genomes):
            raise ValueError("Cyclic dependencies detected in genome settings.")

        return ordered

    def _create_default_genomes(self, annotation: type, param_name: str):
        if annotation is bool:
            return BoolGenome(param_name)

        elif isinstance(annotation, EnumMeta):
            return EnumGenome(param_name)

        elif annotation in [int, float]:
            raise NotImplementedError(f"NumericGenome instance for {param_name} are not defined.")

        elif get_origin(annotation) is Union:
            annotations = get_args(annotation)
            union_genome = UnionGenome(param_name)

            for ann in annotations:
                union_genome.add(self._create_default_genomes(ann, param_name))
            return union_genome

        elif annotation is type(None):
            base_genome = BaseGenome(param_name)
            base_genome.type_value = None
            return base_genome

        else:
            raise ValueError(f"Unknown annotation {annotation} for parameter {param_name}")

    def build(
            self,
            species,
            blacklist_genes: Optional[tuple[str]] = None,
            whitelist_genes: Optional[tuple[str]] = None
    ):
        """
        Build the blueprint for the given species (a class whose __init__ parameters
        are to be evolved). The parameters may be filtered by blacklist or whitelist.
        For each parameter, a genome is created if not already present.
        """
        # Get the constructor parameters of the species.
        c_params: MappingProxyType[str, any] = signature(species).parameters
        filtered_params: dict[str, any] = dict(c_params)

        # Filter parameters according to the provided lists.
        for param_name in list(c_params.keys()):
            if blacklist_genes is not None and param_name in blacklist_genes:
                filtered_params.pop(param_name, None)
            elif whitelist_genes is not None and param_name not in whitelist_genes:
                filtered_params.pop(param_name, None)

        # For each parameter, create or update a genome.
        for param_name, param in filtered_params.items():
            ann = param.annotation
            # If a genome was already added by the user, keep it.
            if param_name in self._genomes and isinstance(self._genomes[param_name], BaseGenome):
                continue
            else:
                self._genomes[param_name] = self._create_default_genomes(ann, param_name)

        graph = self._build_dependency_graph()
        self._genomes = self._topological_sort(graph)

    def add_genome(self, genome: BaseGenome | list[BaseGenome]):
        if not isinstance(genome, list):
            genome = [genome]

        for g in genome:
            self._genomes[g.name] = g

    def remove_genomes(self, genome: str | list[str]):
        if not isinstance(genome, list):
            genome = [genome]

        for g in genome:
            del self._genomes[g]

    def get(self, name: str):
        return self._genomes.get(name)

    def add_market_genome(self, genome: BaseGenome | list[BaseGenome | str] | str, annotation: Optional[type] = None):
        """
        Add market genomes.
        :param genome: The genome or list of genomes to add.
        :param annotation: The annotation of the parameter, only used if for the genome param the name is provided.
        """
        if not isinstance(genome, list):
            genome = [genome]

        for g in genome:
            if not isinstance(g, BaseGenome):
                g = self._create_default_genomes(annotation, g)
            self.market_genomes[g.name] = g

    def remove_market_genome(self, genome: str | list[str]):
        """
        Remove market genomes.
        """
        if not isinstance(genome, list):
            genome = [genome]
        for g in genome:
            if g in self.market_genomes:
                del self.market_genomes[g]

    @staticmethod
    def _create_genome(genome_obj: BaseGenome, context: dict[str, any]):
        if isinstance(genome_obj, UnionGenome):
            genome_obj = random.choice(genome_obj.genome_args)

        if isinstance(genome_obj, NumericGenome):
            return genome_obj.create(context)
        elif isinstance(genome_obj, BoolGenome) or isinstance(genome_obj, EnumGenome):
            return genome_obj.create()
        elif isinstance(genome_obj, BaseGenome):
            return genome_obj.create()
        else:
            raise ValueError(f"Unsupported type {genome_obj} for parameter {genome_obj.name}")

    def create_individual(self):
        """
        Create an individual that includes both species genomes ("dna") and market genomes ("stops").
        This method follows the provided structure:
            - For each parameter in the dependency-ordered species genomes,
              use its annotation to decide how to generate a value.
            - Then, for each market parameter (such as stop loss or take profit),
              generate its value using a randfloat-like function.
        """
        dna: dict[str, any] = {}
        for param_name, genome_obj in self._genomes.items():
            dna[param_name] = self._create_genome(genome_obj, dna)

        env: dict[str, float] = {}
        for feature, genome in self.market_genomes.items():
            env[feature] = self._create_genome(genome, env)

        return {"dna": dna, "env": env}