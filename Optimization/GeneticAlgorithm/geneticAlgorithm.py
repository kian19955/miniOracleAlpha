import logging
import re
from typing import Type, Optional, get_args, get_origin, Union, Any
from collections import OrderedDict, defaultdict
from types import MappingProxyType
from inspect import signature
import random
from time import sleep
from multiprocessing import Pool, Queue
from enum import EnumMeta
import atexit
from copy import deepcopy

from deap import base, creator, tools
import numpy as np

from api.binanceApi import fetch_klines
from backtester import backtest
from oracleMaths import randfloat
from Optimization.GeneticAlgorithm.gaTypes import MateTypeProbabilities, MutateTypeProbabilities
from Optimization.GeneticAlgorithm.operators import gauss_clamp

# TODO: support for list
logger = logging.getLogger("oracle.analysis")

SAFE_BUILTINS = {
    'abs': abs,
    'min': min,
    'max': max,
    'sum': sum,
    'pow': pow,
    'len': len,
    'round': round,
}
SAFE_GLOBALS = {
    '__builtins__': SAFE_BUILTINS
}


class GeneticAlgorithm:
    def __init__(
            self,
            species: Type,
            bt_settings: dict[str, any],
            objectives: dict[str, any],

            genome_settings: dict[str, dict[type, dict[str | type, any]]] = None,
            stop_settings: dict[str, dict[str, float]] = None,

            blacklist_genes: Optional[tuple[str]] = None,
            whitelist_genes: Optional[tuple[str]] = None,
            base_params: Optional[dict[str, any]] = None,

            float_blend: float = 0.5,
            int_blend: bool = False,

            mate_tp: MateTypeProbabilities = MateTypeProbabilities,
            mutate_tp: MutateTypeProbabilities = MutateTypeProbabilities,
            mutation_strength: float = 0.1,

            tournament_size: int = 2,
            hall_of_fame_size: Optional[int] = None,

            elite_injection: Optional[float] = None,
    ):
        """
        :param species: The type of the individual
        :param bt_settings: A dictionary which will be used as the default settings for the backtesting function
        :param objectives: Key is key parameter name of the analysis metrics, value is weight where
            1 tries to get the value as high as possible and
            -1 tries to get the value as low as possible.
        :param genome_settings: These will be used to create a new individual or mutate one. For enums you are allowed to set a probability for each enum value, Enum values not given dont have a chance to mutate into
            genome_settings: dict[str, dict[type, dict[str | type, any]]] = {
                "param1": {
                    float: {"start": float, "stop": float, "step": float},
                    CustomEnum: {CustomEnum.A: 0.1, CustomEnum.B: 0.1}
                }
            }
        :param blacklist_genes: These Genes will be excluded to mutate and evolve.
        :param whitelist_genes: Only these Genes will be included to mutate and evolve.
        :param base_params: These Attributes are always used when creating a new individual. This can be used if genes
            left out to mutate by blacklisting or whitelisting are needed.
        :param float_blend: The strength of the float blend.
        :param int_blend: The strength of the int blend.
        :param mate_tp: The probability for each type to be influenced in the mating two individuals.
        :param mutate_tp: The probability for each type to be influenced in the mutation of an individual.
        :param mutation_strength: The strength of the mutation.
        :param tournament_size: The size of the tournament from which one individual will be selected.
        """
        if blacklist_genes is not None and whitelist_genes is not None:
            raise ValueError("blacklist_genes and whitelist_genes cannot be used together.")

        self.tc: Type = species
        self.bt_settings: dict = bt_settings
        self.objectives: OrderedDict = OrderedDict(objectives)

        self.genome_settings: dict[str, dict[type, dict[str | type, any]]] = genome_settings or {}
        self.stop_settings: dict[str, dict[str, float]] = stop_settings or {}

        self.float_blend = float_blend
        self.int_blend = int_blend

        self.mate_tp = mate_tp
        self.mutate_tp = mutate_tp

        self.mutation_strength = mutation_strength

        self.hall_of_fame_size = hall_of_fame_size
        self.elite_injection = elite_injection

        self.base_params = base_params or {}
        c_params: MappingProxyType[str, any] = signature(species).parameters

        filtered_params: dict[str, any] = dict(c_params)

        for param_name in c_params.keys():
            if blacklist_genes is not None and param_name in blacklist_genes:
                del filtered_params[param_name]
            elif whitelist_genes is not None and param_name not in whitelist_genes:
                del filtered_params[param_name]

        graph = self._build_dependency_graph()
        self.genome_types: OrderedDict[str, type] = self._topological_sort(graph, {
            param_name: param.annotation for param_name, param in filtered_params.items()
        })

        self._validate_genome_settings()

        creator.create("FitnessMax", base.Fitness, weights=tuple(objectives.values()))
        creator.create("Individual", dict, fitness=creator.FitnessMax)

        toolbox = base.Toolbox()
        toolbox.register("individual", tools.initIterate, creator.Individual, self.create_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        toolbox.register("evaluate", self.evaluate)
        toolbox.register("mate", self.mate)
        toolbox.register("mutate", self.mutate)
        toolbox.register("select", tools.selNSGA2)

        self.toolbox = toolbox

        self.eval_counter = 0

    def _validate_genome_settings(self):
        for param_name, annotation in self.genome_types.items():
            if annotation is int or annotation is float:
                if (not 'start' in self.genome_settings[param_name][annotation] or
                        not 'stop' in self.genome_settings[param_name][annotation]):
                    raise ValueError(
                        f"Genome Settings for {param_name} must have a start and a stop value for {annotation}"
                    )

    def _build_dependency_graph(self) -> dict[str, list[str]]:
        logger.info("Building Dependency Graph")
        graph: defaultdict[str, list[str]] = defaultdict(list)
        for param_name, settings in self.genome_settings.items():
            for annotation, config in settings.items():
                if annotation not in (int, float):
                    continue  # Only handle int and float dependencies

                dependencies = []
                # Extract dependencies from start, stop, step
                for key in ['start', 'stop', 'step']:
                    value = config.get(key, None)
                    if isinstance(value, str):
                        relations, parsed_operation = self._extract_relation(value)
                        self.genome_settings[param_name][annotation][key] = parsed_operation
                        dependencies.extend(relations)

                # Add edges from each dependency to the current parameter
                for dep in dependencies:
                    graph[dep].append(param_name)

        return graph

    @staticmethod
    def _extract_relation(operation: str) -> tuple[list[Any], str]:
        return re.findall(r'\{\{([^}]+)}}', operation), re.sub(r"\{\{|}}", "", operation)

    @staticmethod
    def _topological_sort(graph: dict[str, list[str]], param_types: dict[str, type]) -> OrderedDict[str, type]:
        in_degree = {param: 0 for param in param_types}
        for dependent in graph.values():
            for param in dependent:
                in_degree[param] += 1

        queue = [param for param, degree in in_degree.items() if degree == 0]
        species_types = OrderedDict()

        while queue:
            param = queue.pop(0)
            species_types[param] = param_types[param]

            for dependent in graph[param]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(species_types) != len(param_types):
            raise ValueError("Cyclic dependencies detected in genome settings.")

        return species_types

    def run(self, generations: int = 40, population_size: int = 50, use_multiprocessing: bool = True):
        self.eval_counter = 0

        def on_exit():
            if hof and len(hof) > 0:
                for elite in hof:
                    logger.info(f"Best with Fitness: {elite.fitness.values}, Elite: {elite} ")
            else:
                logger.info("No Elites in the Hall of Fame found.")

        atexit.register(on_exit)

        # Create a pool context manager if using multiprocessing
        logger.debug("Creating Pool")
        if use_multiprocessing:
            pool_context = Pool()
        else:
            # Create a dummy pool that runs sequentially
            logger.warning("Multiprocessing is disabled, the operation will take longer.")

            logger.warning("Multiprocessing is disabled, the operation will take longer.")

            class DummyPool:
                @staticmethod
                def map(func, iterable):
                    return list(map(func, iterable))

                @staticmethod
                def imap(func, iterable):
                    return map(func, iterable)

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

            pool_context = DummyPool()

        with pool_context as pool:
            def _eval_individuals(individuals):
                invalid_ind = [ind for ind in individuals if not ind.fitness.valid]
                total_to_evaluate = len(invalid_ind)
                fitnesses = []
                counter = 0
                for fit in pool.imap(self.toolbox.evaluate, invalid_ind):
                    fitnesses.append(fit)
                    counter += 1
                    print(f"Evaluated {counter}/{total_to_evaluate} individuals", end="\r")

                for ind, fit in zip(invalid_ind, fitnesses):
                    ind.fitness.values = fit

            logger.debug("Creating Initial Population")
            hof = tools.HallOfFame(self.hall_of_fame_size) if self.hall_of_fame_size else None

            stats = tools.Statistics(lambda ind: ind.fitness.values)
            stats.register("avg", lambda pop: np.mean([ind.fitness.values for ind in pop], axis=0))
            stats.register("std", lambda pop: np.std([ind.fitness.values for ind in pop], axis=0))
            stats.register("min", lambda pop: np.min([ind.fitness.values for ind in pop], axis=0))
            stats.register("max", lambda pop: np.max([ind.fitness.values for ind in pop], axis=0))

            logger.info("Creating Initial Population")
            population = self.toolbox.population(n=population_size)

            logger.info("Evaluating Initial Population")
            _eval_individuals(population)

            self.eval_counter = 0

            if hof is not None:
                hof.update(population)

            for gen in range(generations):
                logger.debug(f"Running Generation {gen + 1}")
                survivors = self.toolbox.select(population, len(population))
                survivors = list(map(self.toolbox.clone, survivors))

                logger.debug("Mating Survivers")
                for survivor1, survivor2 in zip(survivors[::2], survivors[1::2]):
                    survivor1_changed, survivor2_changed = self.toolbox.mate(survivor1, survivor2)

                    if survivor1_changed:
                        del survivor1.fitness.values
                    if survivor2_changed:
                        del survivor2.fitness.values

                logger.debug("Mutating Offspring")
                for survivor in survivors:
                    if self.toolbox.mutate(survivor):
                        del survivor.fitness.values

                logger.debug("Evaluating Offspring")
                _eval_individuals(survivors)

                if self.elite_injection is not None:
                    population = survivors + list(map(self.toolbox.clone, hof.items[:5]))
                else:
                    population[:] = survivors

                if hof is not None:
                    pareto_front = tools.selNSGA2(population, k=self.hall_of_fame_size)
                    hof.clear()
                    hof.items.extend(pareto_front)

                gen_stats = stats.compile(population)

                logger.info(
                    f"Generation {gen + 1}/{generations}: Best Fitness = {tools.selBest(population, k=1)[0].fitness.values} "
                    f"| Stats: {gen_stats}"
                )
        if hof and len(hof) > 0:
            return hof[0]
        else:
            logger.warning("No valid individual found.")
            return None

    def create_individual(self):
        dna: dict[str, any] = {}
        for param_name, annotation in self.genome_types.items():

            if self.genome_settings.get(param_name, None) is not None and len(
                    self.genome_settings[param_name].keys()) != 1:
                possible_types: list[type] = list(self.genome_settings[param_name].keys())
                annotation = random.choice(possible_types)

            if annotation is float:
                dna[param_name] = randfloat(
                    *self._resolve_genome(
                        param_name,
                        annotation,
                        dna
                    )
                )

            elif annotation is int:
                dna[param_name] = random.randrange(
                    *self._resolve_genome(
                        param_name,
                        annotation,
                        {"dna": dna}
                    )
                )

            elif annotation is bool:
                dna[param_name] = random.choice([True, False])

            elif isinstance(annotation, EnumMeta):
                dna[param_name] = self._retrieve_random_enum(param_name, annotation)

            elif annotation is type(None):
                dna[param_name] = None

            else:
                raise ValueError(f"Unsupported type {annotation} for parameter {param_name}")

        # REMAKE STOPS
        stops: dict[str, float] = {}
        for stop_name, settings in self.stop_settings.items():
            stops[stop_name] = randfloat(
                **settings
            )
        # ------------------

        return {"dna": dna, "stops": stops}

    def evaluate(self, genome):
        # REMAKE stopS
        # ["dna"] and **genome["stops"]
        try:
            individual = self.tc(**(genome["dna"] | self.base_params))

            stats, _ = backtest(
                eval_func=individual.evaluate,
                **self.bt_settings,
                **genome["stops"],
                use_csv=True
            )

            values: list[float | int] = []
            for genome_name, weight in self.objectives.items():
                # Get the value, defaulting to -100 * weight if the key is missing
                value = stats.get(genome_name, -100 * weight)

                if np.isnan(value):
                    value = -100 * weight

                values.append(value)

        except Exception as e:
            logger.error(f"Error evaluating individual: {e}, with Genomes:{(genome | self.base_params)}")
            values: tuple[float | int] = tuple(-100 * weight for weight in self.objectives.values())

        """with self.lock:
            self.indis_processed.value += 1

        print(f"Fitness: {values} individual: {genome} | {self.indis_processed.value}", end="\r")"""

        return tuple(values)

    def mate(self, ind1, ind2) -> tuple[bool, bool]:
        # REMAKE stopS
        # ["dna"]
        initial_indi1 = deepcopy(ind1)
        initial_indi2 = deepcopy(ind2)

        for param_name, annotation in self.genome_types.items():
            roll: float = random.random()

            val1 = ind1["dna"][param_name]
            val2 = ind2["dna"][param_name]

            # Resolve actual type if same (simplifies subsequent handling)
            # In case of Union
            if get_origin(annotation) is Union:
                union_types = get_args(annotation)
                # Check for valid type is in union
                if type(val1) == type(val2) and type(val1) in union_types:
                    annotation = type(val1)

            if annotation is float:
                if roll > self.mate_tp.FLOAT:
                    continue

                gamma: float = (1. + 2. * self.float_blend) * random.random() - self.float_blend
                ind1["dna"][param_name] = (1. - gamma) * val1 + gamma * val2
                ind2["dna"][param_name] = gamma * val1 + (1. - gamma) * val2

                # Clamp the values
                start, stop, _ = self._resolve_genome(param_name, annotation, ind1)
                ind1["dna"][param_name] = max(min(ind1["dna"][param_name], stop), start)
                start, stop, _ = self._resolve_genome(param_name, annotation, ind2)
                ind2["dna"][param_name] = max(min(ind2["dna"][param_name], stop), start)


            elif annotation is int:
                if roll > self.mate_tp.INT:
                    continue

                if self.int_blend:
                    blended_int: int = (val1 + val2) // 2
                    ind1["dna"][param_name], ind2["dna"][param_name] = blended_int, blended_int
                else:
                    ind1["dna"][param_name], ind2["dna"][param_name] = val2, val1

                # Clamp the values
                start, stop, _ = self._resolve_genome(param_name, annotation, ind1)
                ind1["dna"][param_name] = max(min(ind1["dna"][param_name], stop), start)
                start, stop, _ = self._resolve_genome(param_name, annotation, ind2)
                ind2["dna"][param_name] = max(min(ind2["dna"][param_name], stop), start)

            # Unified handling for all other gaTypes (int, Enum, Union, etc.)
            # And Fallback for unsupported gaTypes
            else:
                if isinstance(annotation, EnumMeta):
                    if roll > self.mate_tp.ENUM:
                        continue

                elif get_origin(annotation) is Union:
                    if roll > self.mate_tp.UNION:
                        continue

                elif annotation is bool:
                    if roll > self.mate_tp.BOOL:
                        continue

                else:
                    logger.warning(f"Unsupported type detected when mating for '{param_name}': {annotation}")
                    if roll > self.mate_tp.OTHER:
                        continue

                ind1["dna"][param_name], ind2["dna"][param_name] = val2, val1

        # REMAKE stopS
        for stop_name, stop in self.stop_settings.items():
            if random.random() > self.mate_tp.FLOAT:
                continue

            stop1 = ind1["stops"][stop_name]
            stop2 = ind2["stops"][stop_name]

            gamma = (1. + 2. * self.float_blend) * random.random() - self.float_blend
            ind1["stops"][stop_name] = (1. - gamma) * stop1 + gamma * stop2
            ind2["stops"][stop_name] = gamma * stop1 + (1. - gamma) * stop2

        for stop_name, stop_settings in self.stop_settings.items():
            ind1["stops"][stop_name] = max(min(ind1["stops"][stop_name], stop_settings['stop']), stop_settings['start'])
            ind2["stops"][stop_name] = max(min(ind2["stops"][stop_name], stop_settings['stop']), stop_settings['start'])
        # --------

        for ind in [ind1, ind2]:
            for param_name, annotation in self.genome_types.items():
                if annotation not in [int, float]:
                    continue

                start, stop, _ = self._resolve_genome(param_name, annotation, ind)
                ind["dna"][param_name] = max(min(ind["dna"][param_name], stop), start)

        return tuple(
            (initial_indi1 != ind1, initial_indi2 != ind2)
        )

    def mutate(
            self,
            indi,
            custom_params_settings: Optional[dict[str, any]] = None,
            return_individual: bool = False
    ) -> dict[str, any] | bool:
        """
        Mutate an individual
        
        :param indi: The individual
        :param custom_params_settings: A dictionary which keys are the parameter names and values are the annotation. It will be used instead of self.genome_types
        :param return_individual: Return the mutated individual
        :return: 
            - The mutated individual if return_individual is True
            - Boolean if the individual was mutated. (Only returned if return_individual is False)
        """
        initial_individual = deepcopy(indi)
        
        param_settings: dict[str, any] = custom_params_settings if custom_params_settings is not None \
            else self.genome_types

        for param_name, annotation in param_settings.items():
            roll: float = random.random()
            val: any = indi["dna"][param_name]

            def roll_check(mutate_prob, mutation_func) -> bool:
                if roll < mutate_prob:
                    indi["dna"][param_name] = mutation_func()
                    return True
                return False

            if annotation is float:
                if roll_check(self.mutate_tp.FLOAT, lambda:
                gauss_clamp(
                    val,
                    *self._resolve_genome(param_name, annotation, indi),
                    self.mutation_strength,
                    False
                )):
                    continue

            elif annotation is int:
                if roll_check(self.mutate_tp.INT, lambda:
                gauss_clamp(
                    val,
                    *self._resolve_genome(param_name, annotation, indi),
                    self.mutation_strength,
                    True
                )):
                    continue

            elif annotation is bool:
                if roll > self.mutate_tp.BOOL:
                    continue
                indi["dna"][param_name] = not val

            elif isinstance(annotation, EnumMeta):
                if roll_check(self.mutate_tp.ENUM, lambda:
                self._retrieve_random_enum(param_name, annotation)
                              ):
                    continue

            # Handle Optional (Union with None)
            elif get_origin(annotation) is Union:
                if roll_check(self.mutate_tp.UNION, lambda:
                self._mutate_union(param_name, tuple(t for t in annotation if t is not type(val)))
                              ):
                    continue
                else:
                    indi["dna"][param_name] = self.mutate(
                        {param_name: val},
                        {param_name: type(val)},
                        True
                    )[param_name]

            else:
                logger.warning(f"Unsupported type detected for {param_name}: {annotation}")
                sleep(1)

        # REMAKE stopS
        for stop_name, stop in self.stop_settings.items():
            if random.random() > self.mutate_tp.FLOAT:
                continue
            indi["stops"][stop_name] = gauss_clamp(
                indi["stops"][stop_name],
                stop=stop['stop'],
                start=stop['start'],
                step=stop['step'],
                strength=self.mutation_strength,
            )

        for stop_name, stop in self.stop_settings.items():
            indi["stops"][stop_name] = max(min(indi["stops"][stop_name], self.stop_settings[stop_name]['stop']), self.stop_settings[stop_name]['start'])
        # ---------

        for param_name, annotation in self.genome_types.items():
            if annotation is float or annotation is int:
                start, stop, _ = self._resolve_genome(param_name, annotation, indi)
                indi["dna"][param_name] = max(min(indi["dna"][param_name], stop), start)

        if return_individual:
            return indi
        else:
            return initial_individual != indi

    def _resolve_genome(self, genome: str, annotation: type, individual) -> tuple[float, float, float]:
        start = self.genome_settings[genome][annotation]['start']
        stop = self.genome_settings[genome][annotation]['stop']
        step = self.genome_settings[genome][annotation].get('step', None)

        if isinstance(start, str):
            start = eval(start, SAFE_GLOBALS, dict(individual["dna"], **SAFE_BUILTINS))
        if isinstance(stop, str):
            stop = eval(stop, SAFE_GLOBALS, dict(individual["dna"], **SAFE_BUILTINS))
        if step is not None and isinstance(step, str):
            step = eval(step, SAFE_GLOBALS, dict(individual["dna"], **SAFE_BUILTINS))

        return start, stop, step

    def _mutate_union(self, param_name: str, type_options: tuple[any, ...]):
        arg = random.choice(get_args(type_options))

        if arg is type(None):
            return None

        elif arg is float:
            return randfloat(
                *self._resolve_genome(param_name, arg, self.base_params)
            )
        elif arg is int:
            return random.randrange(
                *self._resolve_genome(param_name, arg, self.base_params)
            )
        elif isinstance(arg, EnumMeta):
            return self._retrieve_random_enum(param_name, arg)

    def _retrieve_random_enum(self, param_name, enum_class):
        try:
            enum_settings: dict[type, any] = self.genome_settings[param_name][enum_class]
            roll = random.uniform(0, sum(enum_settings.values()))

            for enum_value, prob in enum_settings.items():
                roll -= prob
                if roll <= 0:
                    return enum_value

        except KeyError:
            return random.choice(list(enum_class))


if __name__ == '__main__':
    from tradingComponents.indicators import RelativeStrengthIndex, MovingAverageConvergenceDivergence
    from Optimization.GeneticAlgorithm.gaTypes import MateTypeProbabilities, MutateTypeProbabilities
    from logging import DEBUG, INFO
    from custom_logger import setup_logger

    setup_logger('oracle.analysis', INFO, '../../logs/analysis.jsonl', log_in_json=True, stream_in_color=True)

    mutate_tp = MutateTypeProbabilities(
        FLOAT=0.1,
        INT=0.1,
        ENUM=0.1,
        UNION=0.1,
        BOOL=0.1,
        OTHER=0.1
    )
    mate_tp = MateTypeProbabilities(
        FLOAT=0.5,
        INT=0.5,
        ENUM=0.5,
        UNION=0.5,
        BOOL=0.5,
        OTHER=0.5
    )
    g_set: dict[str, dict[type, dict[str | type, any]]] = {
        'fast_period': {
            int: {
                'start': 1,
                'stop': 100,
                'step': 1
            }
        },
        'slow_period': {
            int: {
                'start': '{{fast_period}} + 1',
                'stop': 101,
                'step': 1
            }
        },
        'signal_line_period': {
            int: {
                'start': 1,
                'stop': 80,
                'step': 1
            }
        },
        'momentum_max_lookback': {
            int: {
                'start': 1,
                'stop': 100,
                'step': 1
            }
        },
        'momentum_signal_weight': {
            float: {
                'start': 0.0,
                'stop': 1.0,
                'step': 0.01
            }
        },
        'crossover_max_gradient_degree': {
            float: {
                'start': 0.5,
                'stop': 90.0,
                'step': 0.5
            }
        },
        'crossover_gradient_signal_weight': {
            float: {
                'start': 0.0,
                'stop': 1.0,
                'step': 0.01
            }
        },
        'crossover_weight_impact': {
            float: {
                'start': 0.0,
                'stop': 1.0,
                'step': 0.01
            }
        },
        'zero_line_crossover_weight': {
            float: {
                'start': 0.0,
                'stop': 1.0,
                'step': 0.01
            }
        },
        'zero_line_pullback_lookback': {
            int: {
                'start': 1,
                'stop': 30,
                'step': 1
            }
        },
        'zero_line_pullback_tolerance_percent': {
            float: {
                'start': 0.0,
                'stop': 1.0,
                'step': 0.01
            }
        },
        'zero_line_pullback_weight': {
            float: {
                'start': 0.0,
                'stop': 1.0,
                'step': 0.01
            }
        },
        'magnitude_weight': {
            float: {
                'start': 0.0,
                'stop': 1.0,
                'step': 0.01
            }
        },
        'rate_of_change_weight': {
            float: {
                'start': 0.0,
                'stop': 1.0,
                'step': 0.01
            }
        },
        'weight_impact': {
            float: {
                'start': 0.0,
                'stop': 1.0,
                'step': 0.01
            }
        }
    }

    ga = GeneticAlgorithm(
        species=MovingAverageConvergenceDivergence,
        bt_settings={
            'days': 93,
            'interval': '5m',
            'ticker': "DOGEUSDT",
            'trade_long': True,
            'trade_short': True,
            'leverage': 5,
            'micro_factor': 100000,

        },
        objectives={
            'Sharpe Ratio': 1,
            'Return [%]': 1
        },
        genome_settings=g_set,
        stop_settings={
            'stop_loss': {
                "start": 0.0,
                "stop": 1.0,
                "step": 0.001
            },
            'take_profit': {
                "start": 0.0,
                "stop": 1.0,
                "step": 0.001
            }
        },
        blacklist_genes=('rsi_as_signal',),
        whitelist_genes=None,
        base_params=None,
        int_blend=True,
        mutate_tp=mutate_tp,
        mate_tp=mate_tp,
        mutation_strength=0.1,
        tournament_size=2,
        hall_of_fame_size=5,
        elite_injection=4
    )
    logger.info("Running Genetic Algorithm...")

    print(ga.run(
        generations=250,
        population_size=75,
        use_multiprocessing=True
    ))
