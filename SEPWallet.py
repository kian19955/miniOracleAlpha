import os

import requests
import pandas as pd

from TK import Token

csv_filename = "SEPwallet.csv"
def SEP_wallet_Update():
    # اطلاعات API
    url = "https://api.nobitex.ir/market/trades/list"
    headers = {
        "Authorization": f"Token {Token}"
    }
    params = {
        "srcCurrency": "",
        "dstCurrency": ""
    }

    # ارسال درخواست GET
    response = requests.get(url, headers=headers, params=params)

    # بررسی نتیجه درخواست
    if response.status_code == 200:
        data = response.json()  # تبدیل پاسخ به JSON
        trades = data["trades"]
        if trades != [] :
            trades = data["trades"]
            df = pd.DataFrame(trades)
            selected_columns = ["type", "total", "amount", "fee", "timestamp","market"]
            df_selected = df[selected_columns]

            if os.path.exists(csv_filename):
                df_selected.to_csv(csv_filename, mode='a', index=False, header=False)  # اضافه کردن بدون هدر
            else:
                df_selected.to_csv(csv_filename, index=False)  # ایجاد فایل جدید        print(df_selected)`

    else:
        print(f"Error: {response.status_code}")
        print("Response:", response.text)


def get_SEP_wallet(ticker):
    SEP_wallet_Update()
    try:
        # خواندن فایل CSV
        df = pd.read_csv(csv_filename)

        # فیلتر کردن داده‌ها بر اساس ticker
        filtered_df = df[(df["market"] == ticker) & (df["type"] == "sell")]

        if not filtered_df.empty:
            # دریافت آخرین مقدار total
            last_total = filtered_df.sort_values("timestamp", ascending=False).iloc[0]["total"]
            return last_total
        else:
            return None  # اگر هیچ داده‌ای پیدا نشد
    except FileNotFoundError:
        print(f"File {csv_filename} not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

#print(get_SEP_wallet("ADA-USDT"))
