import random
from enum import EnumMeta
from inspect import signature
from types import MappingProxyType
from collections import defaultdict, OrderedDict
from typing import Optional, get_origin, Union, get_args, Iterator

from .genomes import BaseGenome, BoolGenome, EnumGenome, NumericGenome, UnionGenome

import re

import logging

logger = logging.getLogger("oracle.analysis")

class Species:
    """
   Represents a species blueprint that holds species genomes and market genomes.

   :ivar _genomes: An ordered dictionary mapping parameter names to species genome objects.
   :ivar env_genomes: A dictionary mapping parameter names to market genome objects.
   """
    def __init__(self):
        self._genomes: dict[str, BaseGenome] = OrderedDict()
        self.env_genomes: dict[str, BaseGenome] = {}

    @staticmethod
    def _extract_relation(operation: str) -> tuple[list[str], str]:
        """
        Extract dependency placeholders in the form ``{{param}}`` from the given operation
        and return a tuple containing a list of dependency names and a parsed version of the operation.

        :param operation: The string operation containing placeholders.
        :return: A tuple of the form (list_of_dependency_names, parsed_operation).
        """
        relations = re.findall(r'\{\{([^}]+)}}', operation)
        parsed_operation = re.sub(r"\{\{|}}", "", operation)
        return relations, parsed_operation

    def _build_dependency_graph(self) -> dict[str, list[str]]:
        """
        Iterate over the species genomes and build a dependency graph for numeric genomes.
        For each genome that defines ``start``, ``stop``, or ``step`` as strings, extract
        dependency placeholders and add edges in the graph.

        :return: A dictionary representing the dependency graph.
        """
        graph = defaultdict(list)
        for param_name, genome in self._genomes.items():
            if (isinstance(genome, UnionGenome) and not NumericGenome in genome.genome_args) or not isinstance(genome, NumericGenome):
                continue
            elif isinstance(genome, UnionGenome):
                genomes = [g for g in genome.genome_args if isinstance(g, NumericGenome)]
            else:
                genomes = [genome]

            for g in genomes:
                dependencies = []

                for key in ['start', 'stop', 'step']:
                    value = getattr(g, key, None)

                    if isinstance(value, str):
                        rels, parsed_operation = self._extract_relation(value)
                        setattr(g, key, parsed_operation)
                        dependencies.extend(rels)

                for dep in dependencies:
                    graph[dep].append(param_name)

        return graph

    def _topological_sort(self, graph: dict[str, list[str]]) -> OrderedDict[str, BaseGenome]:
        """
        Perform a topological sort on the dependency graph.

        :param graph: A dictionary mapping parameter names to lists of dependent parameter names.
        :return: An OrderedDict mapping parameter names to genome objects in dependency order.
        :raises ValueError: If cyclic dependencies are detected.
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
        """
        Create a default genome object for a given annotation.

        :param annotation: The type annotation of the parameter.
        :param param_name: The parameter name.
        :return: A genome object appropriate for the annotation.
        :raises NotImplementedError: If a NumericGenome for the parameter is not defined.
        :raises ValueError: If the annotation is unknown.
        """
        if annotation is bool:
            return BoolGenome(param_name)

        elif isinstance(annotation, type) and issubclass(annotation, EnumMeta):
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
        Build the blueprint for the given species. The species is a class whose __init__
        parameters are to be evolved. Optionally filter parameters using a blacklist or whitelist.
        For each parameter, create a default genome if one is not already present.

        :param species: The species class.
        :param blacklist_genes: An optional tuple of parameter names to exclude.
        :param whitelist_genes: An optional tuple of parameter names to include.
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
            if param_name in self._genomes and isinstance(self._genomes[param_name], BaseGenome):
                continue
            else:
                self._genomes[param_name] = self._create_default_genomes(ann, param_name)

        graph = self._build_dependency_graph()
        self._genomes = self._topological_sort(graph)

    @staticmethod
    def _create_genome(genome_obj: BaseGenome, context: dict[str, any]):
        """
        Create a value from a genome object using the provided context.

        :param genome_obj: The genome object.
        :param context: A context dictionary to pass to the create method.
        :return: The generated value.
        :raises ValueError: If the genome type is unsupported.
        """
        if isinstance(genome_obj, (NumericGenome, UnionGenome)):
            return genome_obj.create(context)
        elif isinstance(genome_obj, (BoolGenome, EnumGenome, BaseGenome)):
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
        s: dict[str, any] = {}
        for param_name, genome_obj in self._genomes.items():
            s[param_name] = self._create_genome(genome_obj, s)

        env: dict[str, float] = {}
        for feature, genome in self.env_genomes.items():
            env[feature] = self._create_genome(genome, env)

        return {"self": s, "env": env}

    def iter_all_genomes(self) -> Iterator[BaseGenome]:
        """
        Iterate over all species genomes.
        First iterates over species genomes in the dependency order, then iterates over env genomes.

        :return: An iterator over all species genomes.
        """
        for g in self._genomes.values():
            yield g

        for g in self.env_genomes.values():
            yield g

    def add_genome(self, genome: BaseGenome | list[BaseGenome]):
        """
        Add species genome(s) to the blueprint.

        :param genome: A genome object or list of genome objects.
        """
        if not isinstance(genome, list):
            genome = [genome]

        for g in genome:
            self._genomes[g.name] = g

    def remove_genomes(self, genome_name: str | list[str]):
        """
        Remove species genome(s) by name.

        :param genome_name: A genome name or list of genome names to remove.
        """
        if not isinstance(genome_name, list):
            genome_name = [genome_name]

        for gn in genome_name:
            del self._genomes[gn]

    def add_env_genome(self, genome: BaseGenome | list[BaseGenome | str] | str, annotation: Optional[type] = None):
        """
        Add env genome(s). If a string is provided instead of a genome object,
        a default genome will be created using the given annotation.

        :param genome: A genome object, a string (name), or a list of them.
        :param annotation: The annotation to use if a name is provided.
        """
        if not isinstance(genome, list):
            genome = [genome]

        for g in genome:
            if not isinstance(g, BaseGenome):
                g = self._create_default_genomes(annotation, g)
            self.env_genomes[g.name] = g

    def remove_env_genome(self, genome_names: str | list[str]):
        """
        Remove market genome(s) by name.

        :param genome_names: A genome name or list of genome names to remove.
        """
        if not isinstance(genome_names, list):
            genome_names = [genome_names]
        for gn in genome_names:
            if gn in self.env_genomes:
                del self.env_genomes[gn]

    def get(self, name: str, from_env: bool = False) -> BaseGenome:
        """
        Retrieve a species genome by name.

        :param name: The name of the genome.
        :param from_env: Whether to retrieve from the environment genomes.
        :return: The genome object or None if not found.
        """
        return self.env_genomes.get(name) if from_env else self._genomes.get(name)
