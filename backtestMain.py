import csv

import pandas as pd

from indicators.bollingerBands import bollinger_bands
from indicators.rsi import calculate_rsi_ema
from patterns.S_R_lines import support_and_resistance
from strategies.BB_RSI_Lines import find_closest_line, execute_trade
import random
from deap import base, creator, tools, algorithms


def save_to_csv(file_name, price, response):
    with open(file_name, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([price, response])

def fetch(i):
    data = pd.read_csv("historical_data.csv")
    return data.iloc[i:400+i]

def backtest(W) :
    t = 0
    i = 0
    n = 0
    m = 0
    l = []
    tickers = ["BTCUSDT"]  # لیست تیکرها
    portfolio = {ticker: {"balance": 10000, "coin": 0, "buy_price": None} for ticker in tickers}
    csv_file = "plot_data.csv"

    while t<8321 :
        for ticker in tickers:

            # Fetch data and calculate indicators
            data =fetch(i)
            if t%720 == 0:
                if portfolio["BTCUSDT"]["coin"] != 0:
                    l.append(portfolio["BTCUSDT"]["coin"] * data["Close"].iloc[-1])
                else: l.append(portfolio["BTCUSDT"]["balance"])

            if t == 8320:
                if portfolio["BTCUSDT"]["coin"] != 0:
                    print("avg :",sum(l)/len(l))
                    print(l)
                    return (sum(l) / len(l))

                else:
                    print(l)
                    print("avg :",sum(l)/len(l))
                    return (sum(l) / len(l))



            coin =portfolio[ticker]["coin"]
            balance =portfolio[ticker]["balance"]

            BB = bollinger_bands(data, 20)
            data['RSI'] = calculate_rsi_ema(data['Close'], period=14)
            Rsi = data['RSI'].iloc[-1]
            lines = support_and_resistance(data, 15)
            last_price = data['Close'].iloc[-1]
            nearst_line = find_closest_line(lines, last_price)
            if coin ==0 :
                last_order_type ="sell"
            elif balance==0 :
                last_order_type = "buy"

            # Execute trade
            response = execute_trade(last_price, Rsi, nearst_line, last_order_type, BB.iloc[-1], lines,W,portfolio[ticker]["buy_price"])

            if response[0] == "sell":
                portfolio[ticker]["balance"]=coin*data["Close"].iloc[-1]
                portfolio[ticker]["coin"]=0

                n +=1
            elif response[0] == "sellSL":
                portfolio[ticker]["balance"]=coin*data["Close"].iloc[-1]
                portfolio[ticker]["coin"]=0

                m +=1
            elif response[0] == "buy":
                portfolio[ticker]["coin"]=balance/data["Close"].iloc[-1]
                portfolio[ticker]["balance"] = 0
                portfolio[ticker]["buy_price"] = response[1]


            save_to_csv(csv_file, last_price, response[0])
            # Print trade info if applicable
            if response[0]!=None:
                pass
                #print(response)
            else:pass
                #print("nothing happend")
        i +=1
        t +=1







# تابع هدف: محاسبه بازدهی استراتژی بر اساس ضرایب
def fitness_function(weights):
    # مثال فرضی: ترکیب وزنی سیگنال‌ها
    weighted_sum = backtest(weights)
    # هدف بهینه‌سازی: مثلاً حداکثر کردن سیگنال (قابلیت تغییر)
    return weighted_sum,

# تنظیم فضای مسئله
creator.create("FitnessMax", base.Fitness, weights=(1.0,))  # حداکثرسازی
creator.create("Individual", list, fitness=creator.FitnessMax)

toolbox = base.Toolbox()

# تعریف ژن‌ها: ضرایب در بازه [0, 1]
toolbox.register("attr_float", random.uniform, 0, 2)

# تعریف فرد و جمعیت
toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_float, n=3)  # 4 پارامتر
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# تعریف تابع هدف
toolbox.register("evaluate", fitness_function)

# تعریف عملگرهای ژنتیکی
toolbox.register("mate", tools.cxBlend, alpha=0.5)  # ترکیب
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.1, indpb=0.2)  # جهش
toolbox.register("select", tools.selTournament, tournsize=3)  # انتخاب

# اجرای الگوریتم
def genetic_optimization():
    random.seed(42)  # برای قابلیت بازتولید
    population = toolbox.population(n=50)  # جمعیت اولیه
    generations = 100  # تعداد نسل‌ها

    # آمارگیری
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda x: sum(x) / len(x))
    stats.register("min", min)
    stats.register("max", max)

    # اجرای الگوریتم ژنتیکی
    population, logbook = algorithms.eaSimple(
        population, toolbox, cxpb=0.7, mutpb=0.2, ngen=generations, stats=stats, verbose=True
    )

    # بهترین فرد
    best_individual = tools.selBest(population, k=1)[0]
    return best_individual, best_individual.fitness.values

# اجرا
if __name__ == "__main__":
    best_solution, best_fitness = genetic_optimization()
    print(f"Best Solution: {best_solution}")
    print(f"Best Fitness: {best_fitness}")
