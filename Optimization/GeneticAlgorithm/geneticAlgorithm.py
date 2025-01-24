from typing import Callable, Type, Optional, get_args, get_origin, Union
from types import MappingProxyType
import typing
from inspect import signature
import builtins
import random
from enum import Enum
from dataclasses import dataclass

from deap import base, creator, algorithms, tools

from backtester import backtest
from dataAnalysis import analyze


# TODO: support for list
# TODO: EnumClasses for TypeOperators
# TODO: better var names?

# TODO: MateTypeProbabilities
@dataclass
class MutateTypeProbabilities:
    FLOAT: float = 0.1
    INT = 0.1
    BOOL = 0.1
    ENUM = 0.1
    UNION_CHANGE = 0.1


# These will be used to create a new individual or mutate one,
# For enums you are allowed to set a probability for each enum value, Enum values not given dont have a chance to mutate into
# TODO: use genome Settings
#1. First look for EnumClasses for TypeOperators
{
    "param1": {
        float: {"start": float, "stop": float, "step": float},
        MutateTypeProbabilities: {MutateTypeProbabilities.ENUM: 0.1, MutateTypeProbabilities.UNION_CHANGE: 0.1}
    }
}


class geneticAlgorithm:
    def __init__(
            self,
            tc: Type,
            bt_settings: dict[str, any],
            create_individual: Callable,
            key_genomes: dict[str, any],
            genome_settings: dict[str, dict[type, dict[str | type, any]]] = None,
            blacklist_genes: Optional[tuple[str]] = None,
            whitelist_genes: Optional[tuple[str]] = None,
            base_params: Optional[Type] = None,
            float_blend: Optional[float] = 0.5,
            int_blend: bool = False,
            genome_mate_percentage: float = 0.5,
            mutate_tp: MutateTypeProbabilities = MutateTypeProbabilities
    ):
        """

        :param tc:
        :param bt_settings: Key is parameter name, value is weight where
        1 tries to get the value as high as possible and
        -1 tries to get the value as low as possible.
        :param create_individual:
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
        self.create_individual: Callable = create_individual
        self.key_genomes: dict = key_genomes
        self.genome_settings: dict[str, dict[type, dict[str | type, any]]] = genome_settings

        self.float_blend = float_blend
        self.int_blend = int_blend
        self.genome_mate_percentage = genome_mate_percentage
        self.mutate_tp = mutate_tp

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
        toolbox.register("individual", tools.initIterate, creator.Individual, create_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        toolbox.register("evaluate", self.evaluate)
        toolbox.register("mutate", self.mutate)

    def evaluate(self, individual):
        individual = self.tc(**(individual | self.base_params))

        _, bt_df = backtest(
            eval_func=individual.evaluate,
            ticker=self.bt_settings['ticker'],
            days=self.bt_settings['days'],
            interval=self.bt_settings['interval'],
            trade_long=getattr(self.bt_settings, 'trade_long', True),
            trade_short=getattr(self.bt_settings, 'trade_short', True),
            use_csv=True
        )

        performance: dict[str, any] = analyze(
            target_filename=self.bt_settings['ticker'] + "_" + str(self.bt_settings['days']) + "_" + self.bt_settings[
                'interval'] + ".csv",
            bt_df=bt_df,
            trade_long=getattr(self.bt_settings, 'trade_long', True),
            trade_short=getattr(self.bt_settings, 'trade_short', True),
        )

        values: tuple = tuple(performance[attr] for attr in self.key_genomes.keys())

        return values

    def mate(self, child1, child2):
        for param_name, param in self.tc_params.items():
            if random.random() > self.genome_mate_percentage:
                continue

            annotation = param.annotation
            val1 = child1[param_name]
            val2 = child2[param_name]

            # Resolve actual type if same (simplifies subsequent handling)
            # In case of Union
            if type(val1) == type(val2):
                annotation = type(val1)

            if self.float_blend is not None and annotation is float:
                tools.cxBlend(val1, val2, alpha=self.float_blend)

            if self.int_blend and annotation is int:
                blended_int: int = (val1 + val2) // 2
                child1[param_name], child2[param_name] = blended_int, blended_int

            # Unified handling for all other types (int, Enum, Union, etc.)
            # And Fallback for unsupported types
            else:
                child1[param_name], child2[param_name] = val2, val1

    def mutate(self, individual):
        for param_name, param in self.tc_params.items():
            roll: float = random.random()

            annotation = param.annotation
            val = individual[param_name]

            if annotation is float:
                if roll > self.mutate_tp.FLOAT:
                    continue
                tools.mutGaussian(individual, mu=0, sigma=0.1, indpb=0.1)

            elif annotation is int:
                if roll > self.mutate_tp.INT:
                    continue
                individual[param_name] = random.randrange(
                    self.genome_settings[param_name][int]['start'],
                    self.genome_settings[param_name][int]['stop'],
                    self.genome_settings[param_name][int]['step']
                )

            elif annotation is bool:
                if roll > self.mutate_tp.BOOL:
                    continue
                individual[param_name] = not val

            elif isinstance(annotation, EnumMeta):
                if roll > self.mutate_tp.ENUM:
                    continue
                individual[param_name] = random.choice(list(annotation))

                # Handle Optional (Union with None)
            elif get_origin(annotation) is Union:
                args = get_args(annotation)
                if type(None) in args:
                    if roll <= self.mutate_tp.UNION_NONE:
                        individual[param_name] = None

                elif individual[param_name] is None:
                    # If currently None, assign a random valid value
                    non_none_type = [t for t in get_args(annotation) if t is not type(None)][0]
                    if non_none_type is float:
                        individual[param_name] = random.uniform(0, 1)
                    elif non_none_type is int:
                        individual[param_name] = random.randint(0, 100)
                    elif isinstance(non_none_type, EnumMeta):
                        individual[param_name] = random.choice(list(non_none_type))

                # Fallback for unsupported types
            else:
                if random.random() < 0.1:  # 10% chance to randomize
                    individual[param_name] = random.choice(list(annotation))


if __name__ == '__main__':
    from enum import Enum, EnumType, EnumMeta, IntEnum, auto


    class MyEnum(IntEnum):
        A = 1
        B = 2


    class Test:
        def __init__(self, flo: float, intiger: int, option: Optional[str], enum: MyEnum):
            self.flo = flo
            self.intiger = intiger
            self.option = option
            self.enum = enum


    tc = Test
    tc_params = signature(tc).parameters
    print(tc_params)
    for param_name, param in tc_params.items():
        annotation: Type = param.annotation

        match annotation:
            case builtins.float:
                print(f"{param_name}: Float")
            case builtins.int:
                print(f"{param_name}: Integer")
            case _ if isinstance(annotation, EnumMeta):
                print(f"{param_name}: Enum")
            case _ if hasattr(annotation, '__origin__') and annotation.__origin__ is typing.Union:
                if len(annotation.__args__) == 2 and type(None) in annotation.__args__:
                    print(f"{param_name}: Optional")
                else:
                    print(f"{param_name}: Union")
                print(type(None))
