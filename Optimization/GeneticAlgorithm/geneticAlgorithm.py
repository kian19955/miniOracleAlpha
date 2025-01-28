import logging
from typing import Type, Optional, get_args, get_origin, Union
from collections import OrderedDict
from types import MappingProxyType
from inspect import signature
import random
from time import sleep
from multiprocessing import Pool
from enum import EnumMeta

from deap import base, creator, tools

from api.binanceApi import fetch_klines
from backtester import backtest
from dataAnalysis import analyze
from oracleMaths import randfloat
from Optimization.GeneticAlgorithm.gaTypes import MateTypeProbabilities, MutateTypeProbabilities
from Optimization.GeneticAlgorithm.operators import gauss_clamp

# TODO: support for list

class GeneticAlgorithm:
    def __init__(
            self,
            tc: Type,
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

        :param tc:
        :param bt_settings: Key is parameter name, value is weight where
        1 tries to get the value as high as possible and
        -1 tries to get the value as low as possible.
        :param key_genomes:
        :param genome_settings: These will be used to create a new individual or mutate one. For enums you are allowed to set a probability for each enum value, Enum values not given dont have a chance to mutate into
        genome_settings: dict[str, dict[type, dict[str | type, any]]] = {
            "param1": {
                float: {"start": float, "stop": float, "step": float},
                CustomEnum: {CustomEnum.A: 0.1, CustomEnum.B: 0.1}
            }
        }
        :param blacklist_genes:
        :param whitelist_genes:
        :param base_params: These Attributes are always used when creating a new individual.
        """
        if blacklist_genes is not None and whitelist_genes is not None:
            raise ValueError("blacklist_genes and whitelist_genes cannot be used together.")

        self.tc: Type = tc
        self.bt_settings: dict = bt_settings
        self.key_genomes: OrderedDict = OrderedDict(key_genomes)
        self.genome_settings: dict[str, dict[type, dict[str | type, any]]] = genome_settings or {}

        self.float_blend = float_blend
        self.int_blend = int_blend

        self.mate_tp = mate_tp
        self.mutate_tp = mutate_tp

        self.mutation_strength = mutation_strength

        self.base_params = base_params or {}
        tc_params: MappingProxyType[str, any] = signature(tc).parameters

        filtered_params: dict[str, any] = dict(tc_params)

        for param_name in tc_params.keys():
            if blacklist_genes is not None and param_name in blacklist_genes:
                del filtered_params[param_name]
            elif whitelist_genes is not None and param_name not in whitelist_genes:
                del filtered_params[param_name]

        self.tc_types: dict[str, type] = {}
        for param_name, param in filtered_params.items():
            self.tc_types[param_name] = param.annotation

        self.validate_genome_settings()

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

    def validate_genome_settings(self):
        for param_name, annotation in self.tc_types.items():
            if annotation is int or annotation is float:
                if (not 'start' in self.genome_settings[param_name][annotation] or
                        not 'stop' in self.genome_settings[param_name][annotation]):
                    raise ValueError(
                        f"Genome Settings for {param_name} must have a start and a stop value for {annotation}"
                    )

    def run(self, generations: int = 40, population_size: int = 50, use_multiprocessing: bool = True):
        # Create a pool context manager if using multiprocessing
        logging.debug("Creating Pool")
        if use_multiprocessing:
            pool_context = Pool()
        else:
            # Create a dummy pool that runs sequentially
            logging.warning("Multiprocessing is disabled, the operation will take longer.")
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

            logging.debug("Creating Initial Population")
            population = self.toolbox.population(n=population_size)

            logging.debug("Evaluating Initial Population")
            fitnesses = pool.map(self.toolbox.evaluate, population)
            for ind, fit in zip(population, fitnesses):
                ind.fitness.values = fit

            for gen in range(generations):
                logging.debug(f"Running Generation {gen + 1}")
                survivors = self.toolbox.select(population, len(population))
                survivors = list(map(self.toolbox.clone, survivors))

                logging.debug("Creating Offspring")
                for child1, child2 in zip(survivors[::2], survivors[1::2]):
                    self.toolbox.mate(child1, child2)

                logging.debug("Mutating Offspring")
                for child in survivors:
                    self.toolbox.mutate(child)

                logging.debug("Evaluating Offspring")
                fitnesses = pool.map(self.toolbox.evaluate, survivors)
                for ind, fit in zip(survivors, fitnesses):
                    ind.fitness.values = fit

                population[:] = survivors

                if fallback_fitness is None or tools.selBest(population, k=1)[0].fitness.values[0] > fallback_fitness:
                    fallback_ind = tools.selBest(population, k=1)[0]
                    fallback_fitness = tools.selBest(population, k=1)[0].fitness.values[0]
                logging.info(
                    f"Generation {gen + 1}: Best Fitness = {tools.selBest(population, k=1)[0].fitness.values[0]}")

        best_performer = tools.selBest(population, k=1)[0] \
            if tools.selBest(population, k=1)[0].fitness.values[0] > fallback_fitness else fallback_ind

        logging.info(f"Best Performer: {best_performer}, with Fitness: {best_performer.fitness.values}")
        return best_performer

    def create_individual(self):
        genome: dict[str, any] = {}
        for param_name, annotation in self.tc_types.items():

            if len(self.genome_settings[param_name].keys()) != 1:
                possible_types: list[type] = list(self.genome_settings[param_name].keys())
                annotation = random.choice(possible_types)

            if annotation is float:
                genome[param_name] = randfloat(
                    self.genome_settings[param_name][float]['start'],
                    self.genome_settings[param_name][float]['stop'],
                    self.genome_settings[param_name][float].get('step', None)
                )

            elif annotation is int:
                genome[param_name] = random.randrange(
                    self.genome_settings[param_name][int]['start'],
                    self.genome_settings[param_name][int]['stop'],
                    self.genome_settings[param_name][int].get('step', 1)
                )

            elif isinstance(annotation, EnumMeta):
                genome[param_name] = self._retrieve_random_enum(param_name, annotation)

            elif annotation is type(None):
                genome[param_name] = None

            else:
                raise ValueError(f"Unsupported type {annotation} for parameter {param_name}")

        return genome

    def evaluate(self, individual):
        individual = self.tc(**(individual | self.base_params))
        logging.debug(f"Evaluating Individual {individual}")

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
                logging.warning(f"Info: {genome_name} is None; Total Orders: {performance['total_orders']}")
                genome_value = -100 * weight
            values.append(genome_value)

        return tuple(values)

    def mate(self, ind1, ind2):
        for param_name, annotation in self.tc_types.items():
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

            elif annotation is int:
                if roll > self.mate_tp.INT:
                    continue

                if self.int_blend:
                    blended_int: int = (val1 + val2) // 2
                    ind1[param_name], ind2[param_name] = blended_int, blended_int
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
                    logging.warning(f"Unsupported type detected when mating for '{param_name}': {annotation}")
                    if roll > self.mate_tp.OTHER:
                        sleep(1)
                        continue

                ind1[param_name], ind2[param_name] = val2, val1

    def mutate(
            self,
            individual,
            custom_params_settings: Optional[dict[str, any]] = None,
            return_individual: bool = False
    ) -> dict[str, any] | None:
        param_settings: dict[str, any] = custom_params_settings if custom_params_settings is not None \
            else self.tc_types

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
                    self.genome_settings[param_name][float]['start'],
                    self.genome_settings[param_name][float]['stop'],
                    self.genome_settings[param_name][float].get('step', None),
                    self.mutation_strength,
                    False
                )):
                    continue

            elif annotation is int:
                if roll_check(self.mutate_tp.INT, lambda:
                gauss_clamp(
                    val,
                    self.genome_settings[param_name][int]['start'],
                    self.genome_settings[param_name][int]['stop'],
                    self.genome_settings[param_name][int].get('step', None),
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
                logging.warning(f"Unsupported type detected for {param_name}: {annotation}")
                sleep(1)

        if return_individual:
            return individual

    def _mutate_union(self, param_name: str, type_options: tuple[any, ...]):
        arg = random.choice(get_args(type_options))

        if arg is type(None):
            return None

        elif arg is float:
            return randfloat(
                self.genome_settings[param_name][float]['start'],
                self.genome_settings[param_name][float]['stop'],
                self.genome_settings[param_name][float].get('step', None),
            )
        elif arg is int:
            return random.randrange(
                self.genome_settings[param_name][int]['start'],
                self.genome_settings[param_name][int]['stop'],
                self.genome_settings[param_name][int].get('step', 1),
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
    from tradingComponents.indicators import RelativeStrengthIndex
    from Optimization.GeneticAlgorithm.gaTypes import MateTypeProbabilities, MutateTypeProbabilities

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler()
        ])

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
        'period': {
            int: {
                'start': 1,
                'stop': 100,
                'step': 1
            }
        },
        'lower_band': {
            float: {
                'start': 0,
                'stop': 40,
                'step': 0.1
            }
        },
        'upper_band': {
            float: {
                'start': 60,
                'stop': 100,
                'step': 0.1
            }
        }
    }

    logging.info("Creating Genetic Algorithm...")

    ga = GeneticAlgorithm(
        tc=RelativeStrengthIndex,
        bt_settings={
            'ticker': 'SOLUSDT',
            'days': 165,
            'interval': '1h',
            'trade_long': True,
            'trade_short': True,
        },
        key_genomes={
            'sharpe_ratio': 1,
        },
        genome_settings=g_set,
        blacklist_genes=('rsi_as_signal',),
        whitelist_genes=None,
        base_params=None,
        int_blend=False,
        mutate_tp=mutate_tp,
        mate_tp=mate_tp,
        mutation_strength=0.1,
        tournament_size=2
    )

    logging.info("Running Genetic Algorithm...")

    print(ga.run(
        generations=40,
        population_size=4,
        use_multiprocessing=True
    ))
