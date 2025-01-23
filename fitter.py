from deap import base, creator, tools, algorithms
import random
import multiprocessing

from backtester import backtest
from dataAnalysis import analyze
from tradingComponents.indicators import RelativeStrengthIndex

# Define parameter ranges
param_ranges = {
    'period': (7, 21),  # Integer (RSI period)
    'lower_band': (20.0, 40.0),  # Float (lower band)
    'upper_band': (60.0, 80.0)  # Float (upper band)
}

# Define fitness strategy: maximize Sharpe ratio
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)

# Initialize toolbox
toolbox = base.Toolbox()

# Function to create an individual
def create_individual():
    return [
        random.randint(*param_ranges['period']),  # Integer
        random.uniform(*param_ranges['lower_band']),  # Float
        random.uniform(*param_ranges['upper_band'])  # Float
    ]

toolbox.register("individual", tools.initIterate, creator.Individual, create_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# Fitness evaluation function
def evaluate(individual):
    params = {
        'period': int(individual[0]),  # Ensure period is an integer
        'lower_band': individual[1],
        'upper_band': individual[2]
    }

    # Initialize RSI strategy
    tc = RelativeStrengthIndex(**params)

    # Backtest
    his_df, bt_df = backtest(
        eval_func=tc.evaluate,
        ticker="DOGEUSDT",
        days=0.03333333333333333333,
        interval="1s",
        trade_long=True,
        trade_short=True,
        use_csv=True
    )


    # Analyze results
    analysis = analyze(
        his_df=his_df,
        bt_df=bt_df,
        trade_long=True,
        trade_short=True,
        target_filename="",
        print_info=False
    )
    sharpe_ratio = analysis['sharpe_ratio']
    if not isinstance(sharpe_ratio, (float, int)):  # Ensure sharpe_ratio is numeric
        sharpe_ratio = -100  # Penalize invalid results
    return (sharpe_ratio,)

toolbox.register("evaluate", evaluate)

# Evolutionary operators
toolbox.register("mate", tools.cxBlend, alpha=0.5)  # Blend crossover for floats
toolbox.register("mutate", tools.mutUniformInt, low=param_ranges['period'][0], up=param_ranges['period'][1], indpb=0.1)  # Integer mutation
toolbox.register("select", tools.selTournament, tournsize=3)  # Tournament selection

if __name__ == '__main__':
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()

    # Parallelization
    pool = multiprocessing.Pool()
    toolbox.register("map", pool.map)

    # Initialize population
    population = toolbox.population(n=50)

    # Track best individual and Sharpe ratio
    best_individual = None
    best_sharpe = []

    # Run GA
    for gen in range(40):
        population = algorithms.varAnd(population, toolbox, cxpb=0.7, mutpb=0.2)
        fits = toolbox.map(toolbox.evaluate, population)
        for ind, fit in zip(population, fits):
            ind.fitness.values = fit

        # Track best individual
        current_best = tools.selBest(population, k=1)[0]
        best_sharpe.append(current_best.fitness.values[0])

        if best_individual is None or current_best.fitness.values[0] > best_individual.fitness.values[0]:
            best_individual = current_best

        print(f"Generation {gen + 1}: Best Sharpe = {current_best.fitness.values[0]}")

    # Print final results
    print("Best Parameters:", best_individual)
    print("Best Sharpe Ratio:", best_individual.fitness.values[0])

    # Close multiprocessing pool
    pool.close()
    pool.join()