import pandas as pd
import matplotlib.pyplot as plt

# خواندن فایل CSV
csv_file = "plot_data.csv"
data = pd.read_csv(csv_file)

# فرض کنید فایل trade_data.csv دو ستون دارد: Price و Response

# فیلتر کردن داده‌های خرید و فروش
buy_points = data[data["Response"] == "buy"]
sell_points = data[data["Response"] == "sell"]

# رسم نمودار
plt.figure(figsize=(12, 6))

# رسم قیمت‌ها
plt.plot(data.index, data["Price"], label="Price", color="blue", alpha=0.7)

# اضافه کردن نقاط خرید و فروش
plt.scatter(buy_points.index, buy_points["Price"], color="green", label="Buy", marker="^", s=100)
plt.scatter(sell_points.index, sell_points["Price"], color="red", label="Sell", marker="v", s=100)

# تنظیمات نمودار
plt.title("Trading Points on Price Chart")
plt.xlabel("Index")
plt.ylabel("Price")
plt.legend()
plt.grid(alpha=0.3)

# نمایش نمودار
plt.show()
