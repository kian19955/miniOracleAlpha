import logging
import re
from typing import Type, Optional, get_args, get_origin, Union
from collections import OrderedDict, defaultdict
from types import MappingProxyType
from inspect import signature
import random
from time import sleep
from multiprocessing import Pool
from enum import EnumMeta
import atexit

from deap import base, creator, tools

from api.binanceApi import fetch_klines
from backtester import backtest
from dataAnalysis import analyze
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
            key_genomes: dict[str, any],

            genome_settings: dict[str, dict[type, dict[str | type, any]]] = None,

            blacklist_genes: Optional[tuple[str]] = None,
            whitelist_genes: Optional[tuple[str]] = None,
            base_params: Optional[dict[str, any]] = None,

            float_blend: float = 0.5,
            int_blend: bool = False,

            mate_tp: MateTypeProbabilities = MateTypeProbabilities,
            mutate_tp: MutateTypeProbabilities = MutateTypeProbabilities,
            mutation_strength: float = 0.1,

            tournament_size: int = 2
    ):
        """

        :param species: The type of the individual
        :param bt_settings: A dictionary which will be used as the default settings for the backtesting function
        :param key_genomes: Key is key parameter name of the analysis metrics, value is weight where
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
        self.key_genomes: OrderedDict = OrderedDict(key_genomes)
        self.genome_settings: dict[str, dict[type, dict[str | type, any]]] = genome_settings or {}

        self.float_blend = float_blend
        self.int_blend = int_blend

        self.mate_tp = mate_tp
        self.mutate_tp = mutate_tp

        self.mutation_strength = mutation_strength

        self.base_params = base_params or {}
        tc_params: MappingProxyType[str, any] = signature(species).parameters

        filtered_params: dict[str, any] = dict(tc_params)

        for param_name in tc_params.keys():
            if blacklist_genes is not None and param_name in blacklist_genes:
                del filtered_params[param_name]
            elif whitelist_genes is not None and param_name not in whitelist_genes:
                del filtered_params[param_name]

        self.genome_types: dict[str, type] = {}
        for param_name, param in filtered_params.items():
            self.genome_types[param_name] = param.annotation

        self.genome_types: OrderedDict[str, type] = OrderedDict(self.genome_types)

        print(self._build_dependency_graph())
        exit()

        self._validate_genome_settings()

        fetch_klines(
            ticker=self.bt_settings['ticker'],
            interval=self.bt_settings['interval'],
            days=self.bt_settings['days'],
        )

        creator.create("FitnessMax", base.Fitness, weights=tuple(key_genomes.values()))
        creator.create("Individual", dict, fitness=creator.FitnessMax)

        toolbox = base.Toolbox()
        toolbox.register("individual", tools.initIterate, creator.Individual, self.create_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        toolbox.register("evaluate", self.evaluate)
        toolbox.register("mate", self.mate)
        toolbox.register("mutate", self.mutate)
        toolbox.register("select", tools.selTournament, tournsize=tournament_size)

        self.toolbox = toolbox

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
                if annotation is not int and annotation is not float:
                    continue

                if isinstance(config.get('start'), str):
                    rel = self._extract_relation(config['start'])
                    graph[param_name].extend(rel)
                if isinstance(config.get('stop'), str):
                    graph[param_name].extend(self._extract_relation(config['stop']))
                if isinstance(config.get('step'), str):
                    graph[param_name].extend(self._extract_relation(config['step']))

        return graph

    @staticmethod
    def _extract_relation(operation: str) -> list[str]:
        return re.findall(r'\{([^}]+)\}', operation)

    def _topological_sort(self, graph: dict[str, list[str]]) -> OrderedDict[str, type]:
        in_degree = {param: 0 for param in self.genome_types}
        for param, deps in graph.items():
            for dep in deps:
                in_degree[dep] += 1

        queue = [param for param, degree in in_degree.items() if degree == 0]
        sorted_order = []

        while queue:
            param = queue.pop(0)
            sorted_order.append(param)

            for dependent in graph[param]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(sorted_order) != len(self.genome_types):
            raise ValueError("Cyclic dependencies detected in genome settings.")

        return sorted_order

    def run(self, generations: int = 40, population_size: int = 50, use_multiprocessing: bool = True):
        def on_exit():
            print(f"Best Fallback Performer {fallback_ind} with Fitness: {fallback_fitness}")

        atexit.register(on_exit)

        # Create a pool context manager if using multiprocessing
        logger.debug("Creating Pool")
        if use_multiprocessing:
            pool_context = Pool()
        else:
            # Create a dummy pool that runs sequentially
            logger.warning("Multiprocessing is disabled, the operation will take longer.")

            class DummyPool:
                @staticmethod
                def map(func, iterable):
                    return list(map(func, iterable))

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

            pool_context = DummyPool()

        with pool_context as pool:
            fallback_ind = None
            fallback_fitness = None

            logger.debug("Creating Initial Population")
            population = self.toolbox.population(n=population_size)

            logger.debug("Evaluating Initial Population")
            fitnesses = pool.map(self.toolbox.evaluate, population)
            for ind, fit in zip(population, fitnesses):
                ind.fitness.values = fit

            for gen in range(generations):
                logger.debug(f"Running Generation {gen + 1}")
                survivors = self.toolbox.select(population, len(population))
                survivors = list(map(self.toolbox.clone, survivors))

                logger.debug("Creating Offspring")
                for child1, child2 in zip(survivors[::2], survivors[1::2]):
                    self.toolbox.mate(child1, child2)

                logger.debug("Mutating Offspring")
                for child in survivors:
                    self.toolbox.mutate(child)

                logger.debug("Evaluating Offspring")
                fitnesses = pool.map(self.toolbox.evaluate, survivors)
                for ind, fit in zip(survivors, fitnesses):
                    ind.fitness.values = fit

                population[:] = survivors

                if fallback_fitness is None or tools.selBest(population, k=1)[0].fitness.values[0] > fallback_fitness:
                    fallback_ind = tools.selBest(population, k=1)[0]
                    fallback_fitness = tools.selBest(population, k=1)[0].fitness.values[0]
                logger.info(
                    f"Generation {gen + 1}/{generations}: Best Fitness = {tools.selBest(population, k=1)[0].fitness.values}")

        best_performer = tools.selBest(population, k=1)[0] \
            if tools.selBest(population, k=1)[0].fitness.values[0] > fallback_fitness else fallback_ind

        logger.info(f"Best Fitness: {best_performer.fitness.values} with Performer: {best_performer}, ")
        return best_performer

    def create_individual(self):
        individual: dict[str, any] = {}
        for param_name, annotation in self.genome_types.items():

            if self.genome_settings.get(param_name, None) is not None and len(self.genome_settings[param_name].keys()) != 1:
                possible_types: list[type] = list(self.genome_settings[param_name].keys())
                annotation = random.choice(possible_types)

            if annotation is float:
                individual[param_name] = randfloat(
                    *self._resolve_genome(
                        param_name,
                        annotation,
                        individual
                    )
                )

            elif annotation is int:
                individual[param_name] = random.randrange(
                    *self._resolve_genome(
                        param_name,
                        annotation,
                        individual
                    )
                )

            elif annotation is bool:
                individual[param_name] = random.choice([True, False])

            elif isinstance(annotation, EnumMeta):
                individual[param_name] = self._retrieve_random_enum(param_name, annotation)

            elif annotation is type(None):
                individual[param_name] = None

            else:
                raise ValueError(f"Unsupported type {annotation} for parameter {param_name}")

        return individual

    def evaluate(self, genome):
        try:
            individual = self.tc(**(genome | self.base_params))

            _, bt_df = backtest(
                eval_func=individual.evaluate,
                **self.bt_settings,
                use_csv=True
            )

            performance: dict[str, any] = analyze(
                target_filename=self.bt_settings['ticker'] + "_" + str(self.bt_settings['days']) + "_" + self.bt_settings[
                    'interval'] + ".csv",
                bt_df=bt_df,
                trade_long=self.bt_settings.get('trade_long', True),
                trade_short=self.bt_settings.get('trade_short', True),
                print_details=False
            )

            values: list[float | int] = []
            for genome_name, weight in self.key_genomes.items():
                genome_value = performance[genome_name]
                if genome_value is None:
                    logger.warning(f"Info: {genome_name} is None; Total Orders: {performance['total_orders']}")
                    genome_value = -100 * weight
                values.append(genome_value)

            logger.info(f"Finished evaluating individual: {individual}")

        except Exception as e:
            logger.error(f"Error evaluating individual: {e}, with Genomes:{(genome | self.base_params)}")
            values: tuple[float | int] = tuple(-100 * weight for weight in self.key_genomes.values())

        return tuple(values)

    def mate(self, ind1, ind2):
        for param_name, annotation in self.genome_types.items():
            roll: float = random.random()

            val1 = ind1[param_name]
            val2 = ind2[param_name]

            # Resolve actual type if same (simplifies subsequent handling)
            # In case of Union
            if type(val1) == type(val2):
                annotation = type(val1)

            if annotation is float:
                if roll > self.mate_tp.FLOAT:
                    continue

                gamma = (1. + 2. * self.float_blend) * random.random() - self.float_blend
                ind1[param_name] = (1. - gamma) * val1 + gamma * val2
                ind2[param_name] = gamma * val1 + (1. - gamma) * val2

                # Clamp the values
                start, stop, _ = self._resolve_genome(param_name, annotation, ind1)
                ind1[param_name] = max(min(ind1[param_name], stop), start)
                start, stop, _ = self._resolve_genome(param_name, annotation, ind2)
                ind2[param_name] = max(min(ind2[param_name], stop), start)


            elif annotation is int:
                if roll > self.mate_tp.INT:
                    continue

                if self.int_blend:
                    blended_int: int = (val1 + val2) // 2
                    ind1[param_name], ind2[param_name] = blended_int, blended_int

                    # Clamp the values
                    start, stop, _ = self._resolve_genome(param_name, annotation, ind1)
                    ind1[param_name] = max(min(ind1[param_name], stop), start)
                    start, stop, _ = self._resolve_genome(param_name, annotation, ind2)
                    ind2[param_name] = max(min(ind2[param_name], stop), start)
                else:
                    ind1[param_name], ind2[param_name] = val2, val1

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

                ind1[param_name], ind2[param_name] = val2, val1

    def mutate(
            self,
            individual,
            custom_params_settings: Optional[dict[str, any]] = None,
            return_individual: bool = False
    ) -> dict[str, any] | None:
        param_settings: dict[str, any] = custom_params_settings if custom_params_settings is not None \
            else self.genome_types

        for param_name, annotation in param_settings.items():
            roll: float = random.random()
            val: any = individual[param_name]

            def roll_check(mutate_prob, mutation_func) -> bool:
                if roll < mutate_prob:
                    individual[param_name] = mutation_func()
                    return True
                return False

            if annotation is float:
                if roll_check(self.mutate_tp.FLOAT, lambda:
                gauss_clamp(
                    val,
                    *self._resolve_genome(param_name, annotation, individual),
                    self.mutation_strength,
                    False
                )):
                    continue

            elif annotation is int:
                if roll_check(self.mutate_tp.INT, lambda:
                gauss_clamp(
                    val,
                    *self._resolve_genome(param_name, annotation, individual),
                    self.mutation_strength,
                    True
                )):
                    continue

            elif annotation is bool:
                if roll > self.mutate_tp.BOOL:
                    continue
                individual[param_name] = not val

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
                    individual[param_name] = self.mutate(
                        {param_name: val},
                        {param_name: type(val)},
                        True
                    )[param_name]

            else:
                logger.warning(f"Unsupported type detected for {param_name}: {annotation}")
                sleep(1)

        if return_individual:
            return individual

    def _resolve_genome(self, genome: str, annotation: type, individual) -> tuple[float, float, float]:
        start = self.genome_settings[genome][annotation]['start']
        stop = self.genome_settings[genome][annotation]['stop']
        step = self.genome_settings[genome][annotation].get('step', None)

        if isinstance(start, str):
            start = eval(start, SAFE_GLOBALS, (individual | SAFE_BUILTINS))
        if isinstance(stop, str):
            stop = eval(stop, SAFE_GLOBALS, (individual | SAFE_BUILTINS))
        if step is not None and isinstance(step, str):
            step = eval(step, SAFE_GLOBALS, (individual | SAFE_BUILTINS))

        if stop <= start:
            raise ValueError(f"Invalid range for {genome}: stop ({stop}) must be greater than start ({start}).")

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
    from logging import DEBUG
    from custom_logger import setup_logger

    setup_logger('oracle.analysis', DEBUG, '../../logs/analysis.jsonl', log_in_json=True, stream_in_color=True)

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
    print(GeneticAlgorithm._extract_relation("{wow} + 1"))
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
                'start': '{fast_period} + 1',
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
                'start': 0.0,
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

    logger.info("Creating Genetic Algorithm...")

    ga = GeneticAlgorithm(
        species=MovingAverageConvergenceDivergence,
        bt_settings={
            'ticker': 'SOLUSDT',
            'days': 7,
            'interval': '1m',
            'trade_long': True,
            'trade_short': True,
        },
        key_genomes={
            'sharpe_ratio': 1,
            'total_profit': 1
        },
        genome_settings=g_set,
        blacklist_genes=None,
        whitelist_genes=None,
        base_params=None,
        int_blend=False,
        mutate_tp=mutate_tp,
        mate_tp=mate_tp,
        mutation_strength=0.1,
        tournament_size=2
    )

    logger.info("Running Genetic Algorithm...")

    print(ga.run(
        generations=50,
        population_size=15,
        use_multiprocessing=True
    ))
