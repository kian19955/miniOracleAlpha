import logging
from typing import Type, Optional, get_args, get_origin, Union
from types import MappingProxyType
from inspect import signature
import random
from time import sleep
from multiprocessing import Pool
from enum import EnumMeta

from deap import base, creator, tools

from backtester import backtest
from dataAnalysis import analyze
from oracleMaths import randfloat
from Optimization.GeneticAlgorithm.types import MateTypeProbabilities, MutateTypeProbabilities
from Optimization.GeneticAlgorithm.operators import gauss_clamp


# TODO: support for list
# TODO: better var names?

# TODO: move all operations to independent operator functions

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

        self.validate_genome_settings(genome_settings)

        self.tc: Type = tc
        self.bt_settings: dict = bt_settings
        self.key_genomes: dict = key_genomes
        self.genome_settings: dict[str, dict[type, dict[str | type, any]]] = genome_settings

        self.int_blend = int_blend

        self.mate_tp = mate_tp
        self.mutate_tp = mutate_tp

        self.mutation_strength = mutation_strength

        self.base_params = base_params
        self.tc_params = signature(tc.__init__).parameters

        mutable_params = dict(self.tc_params)

        for param_name in self.tc_params.keys():
            if blacklist_genes is not None and param_name in blacklist_genes:
                del mutable_params[param_name]
            elif whitelist_genes is not None and param_name not in whitelist_genes:
                del mutable_params[param_name]

        self.tc_params = MappingProxyType(mutable_params)

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


    def validate_genome_settings(self, genome_settings):
        for param_name, param in self.tc_params.items():
            annotation = param.annotation

            if annotation is int or annotation is float:
                if not hasattr(self.genome_settings[param_name][annotation], 'start') or not hasattr(
                        self.genome_settings[param_name][annotation], 'stop'):
                    raise ValueError(
                        f"Genome Settings for {param_name} must have a start and a stop value for {annotation}"
                    )

    def run(self, generations: int = 40, population: int = 50):
        pool = Pool()
        self.toolbox.register("map", pool.map)

        population: list = self.toolbox.population(n=population)

        fitnesses = self.toolbox.map(self.toolbox.evaluate, population)
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit

        for gen in range(generations):
            survivers = self.toolbox.select(population, len(population))
            survivers = list(map(self.toolbox.clone, survivers))

            # Mating
            for child1, child2 in zip(survivers[::2], survivers[1::2]):
                self.toolbox.mate(child1, child2)

            for child in survivers:
                self.toolbox.mutate(child)

            # Evaluate the individuals with an invalid fitness
            fitnesses = self.toolbox.map(self.toolbox.evaluate, survivers)
            for ind, fit in zip(survivers, fitnesses):
                ind.fitness.values = fit

            population[:] = survivers

            print(f"Generation {gen + 1}: Best Sharpe = {tools.selBest(population, k=1)[0].fitness.values[0]}")

        pool.close()
        pool.join()

        return population

    def create_individual(self):
        genome: dict[str, any] = {}
        for param_name, param in self.tc_params.items():
            possible_types: list[type] = list(self.genome_settings[param_name].keys())
            chosen_type: type = random.choice(possible_types)

            if chosen_type is float:
                genome[param_name] = randfloat(
                    self.genome_settings[param_name][float]['start'],
                    self.genome_settings[param_name][float]['stop'],
                    self.genome_settings[param_name][float].get('step', None)
                )

            if chosen_type is int:
                genome[param_name] = random.randrange(
                    self.genome_settings[param_name][int]['start'],
                    self.genome_settings[param_name][int]['stop'],
                    self.genome_settings[param_name][int].get('step', 1)
                )

            if isinstance(chosen_type, EnumMeta):
                genome[param_name] = self._retrieve_random_enum(param_name, chosen_type)

            if chosen_type is type(None):
                genome[param_name] = None

            else:
                raise ValueError(f"Unsupported type {chosen_type}")

    def evaluate(self, individual):
        individual = self.tc(**(individual | self.base_params))

        _, bt_df = backtest(
            eval_func=individual.evaluate,
            ticker=self.bt_settings['ticker'],
            days=self.bt_settings['days'],
            interval=self.bt_settings['interval'],
            trade_long=self.bt_settings.get('trade_long', True),
            trade_short=self.bt_settings.get('trade_short', True),
            use_csv=True
        )

        performance: dict[str, any] = analyze(
            target_filename=self.bt_settings['ticker'] + "_" + str(self.bt_settings['days']) + "_" + self.bt_settings[
                'interval'] + ".csv",
            bt_df=bt_df,
            trade_long=self.bt_settings.get('trade_long', True),
            trade_short=self.bt_settings.get('trade_short', True),
        )

        values: tuple = tuple(performance[attr] for attr in self.key_genomes.keys())

        return values

    def mate(self, child1, child2):
        for param_name, param in self.tc_params.items():
            roll: float = random.random()

            annotation = param.annotation
            val1 = child1[param_name]
            val2 = child2[param_name]

            # Resolve actual type if same (simplifies subsequent handling)
            # In case of Union
            if type(val1) == type(val2):
                annotation = type(val1)

            if annotation is float:
                if roll > self.mate_tp.FLOAT:
                    continue

                tools.cxBlend(val1, val2, alpha=self.float_blend)

            if self.int_blend and annotation is int:
                if roll > self.mate_tp.INT:
                    continue

                blended_int: int = (val1 + val2) // 2
                child1[param_name], child2[param_name] = blended_int, blended_int

            # Unified handling for all other types (int, Enum, Union, etc.)
            # And Fallback for unsupported types
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
                    logging.warning(f"Unsupported type detected when mating for {param_name}: {annotation}")
                    if roll > self.mate_tp.OTHER:
                        sleep(1)
                        continue

                child1[param_name], child2[param_name] = val2, val1

    def mutate(
            self,
            individual,
            custom_params_settings: Optional[dict[str, any]] = None,
            return_individual: bool = False
    ) -> dict[str, any] | None:
        param_settings: dict[str, any] = custom_params_settings if custom_params_settings is not None \
            else self.tc_params

        for param_name, param in param_settings.items():
            roll: float = random.random()
            annotation = param.annotation
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
                    False,
                    self.mutation_strength
                )):
                    continue

            elif annotation is int:
                if roll_check(self.mutate_tp.INT, lambda:
                gauss_clamp(
                    val,
                    self.genome_settings[param_name][int]['start'],
                    self.genome_settings[param_name][int]['stop'],
                    self.genome_settings[param_name][int].get('step', None),
                    True,
                    self.mutation_strength
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
                    self._mutate_union(param_name, annotation)
                ):
                    continue
                else:
                    individual[param_name] = self.mutate(
                        {param_name: val},
                        {self.tc_params[param_name].name: self.tc_params[param_name]},
                        True
                    )[param_name]

            else:
                logging.warning(f"Unsupported type detected for {param_name}: {annotation}")
                sleep(1)

        if return_individual:
            return individual

    def _mutate_union(self, param_name: str, annotation: tuple[any, ...]):
        arg = random.choice(get_args(annotation))

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
    from Optimization.GeneticAlgorithm.types import MateTypeProbabilities, MutateTypeProbabilities

    mutate_tp = MutateTypeProbabilities(
        FLOAT=0.1,
        INT=0.1,
        ENUM=0.1,
        UNION=0.1,
        BOOL=0.1
    )
    mate_tp = MateTypeProbabilities(
        FLOAT=0.5,
        INT=0.5,
        ENUM=0.5,
        UNION=0.5,
        BOOL=0.5
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

    ga = GeneticAlgorithm(
        tc=RelativeStrengthIndex,
        bt_settings={
            'ticker': 'SOLUSDT',
            'days': 14,
            'interval': '1h',
            'trade_long': True,
            'trade_short': True,
        },
        key_genomes={
            'rsi_as_signal': 0.5,
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

    print(ga.run(
        generations=40,
        population=50
    ))