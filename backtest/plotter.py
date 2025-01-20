import pandas as pd
import matplotlib.pyplot as plt

# خواندن فایل CSV
csv_file = "plot_data.csv"
data = pd.read_csv(csv_file)

# فرض کنید فایل trade_data.csv دو ستون دارد: Price و Response

# فیلتر کردن داده‌های خرید و فروش
buy_points = data[data["Response"] == "buy"]
sell_points = data[data["Response"] == "sell"]
sellSL_points = data[data["Response"] == "sellSL"]


# رسم نمودار
plt.figure(figsize=(12, 6))

# رسم قیمت‌ها
plt.plot(data.index, data["Price"], label="Price", color="blue", alpha=0.7)

# اضافه کردن نقاط خرید و فروش
plt.scatter(buy_points.index, buy_points["Price"], color="green", label="Buy", marker="^", s=100)
plt.scatter(sell_points.index, sell_points["Price"], color="red", label="Sell", marker="v", s=100)
plt.scatter(sellSL_points.index, sellSL_points["Price"], color="pink", label="SellSL", marker="v", s=100)
plt.plot(data["BBU"].index,data["BBU"], linestyle='-', color='green', label='Bollinger Upper')
plt.plot(data["BBL"].index,data["BBL"], linestyle='-', color='red', label='Bollinger Lower')

plt.plot(data["SMA"].index,data["SMA"], linestyle='-', color='black', label='SMA')
plt.fill_between(data["BBL"].index, data["BBU"],data["BBL"], color='lightgrey', alpha=0.3, label='Bollinger Band')


# تنظیمات نمودار
plt.title("Trading Points on Price Chart")
plt.xlabel("Index")
plt.ylabel("Price")
plt.legend()
plt.grid(alpha=0.3)

# نمایش نمودار
plt.show()
