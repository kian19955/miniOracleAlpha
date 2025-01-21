import pandas as pd
from matplotlib import pyplot as plt

from tradingComponents.indicators.bollingerBands import bollinger_bands

csv_file = "plot_data.csv"
data = pd.read_csv(csv_file)
percent_change=[]
buy_points = data[data["Response"] == "buy"]
sell_points = data[data["Response"].isin(["sell", "sellSL"])]
df = pd.read_csv("historical_data.csv")
BB = bollinger_bands(df,20)

for i in range(0, len(buy_points)-1):
    # فرض می‌کنیم ستون قیمت 'Price' نام دارد
    buy_price = float(buy_points.iloc[i]["Price"])
    sell_price = float(sell_points.iloc[i]["Price"])

    # محاسبه درصد تغییر
    percent_change.append(round(((sell_price - buy_price) / buy_price) * 100,2))

data =percent_change
print("PL ratio :",len([i for i in data if i >0])/len([i for i in data if i<0]))
print(len([i for i in data if i >0 ]))
print((data))
# رسم نمودار
plt.figure(figsize=(12, 6))  # تنظیم اندازه نمودار
plt.plot(data, marker='o', linestyle='-', color='b', label='Price')
# تنظیمات نمودار
plt.title("Data Plot", fontsize=16)
plt.xlabel("Index", fontsize=12)
plt.ylabel("Value", fontsize=12)
plt.axhline(0, color='black', linewidth=0.8, linestyle='--')  # اضافه کردن خط صفر
plt.legend()
plt.grid(alpha=0.4)

# نمایش نمودار
plt.show()