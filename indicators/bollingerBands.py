import pandas as pd
def bollinger_bands (df,window):

    num_std_dev = 2  # تعداد انحراف معیار (معمولاً 2)

    # محاسبه میانگین متحرک ساده (SMA)
    df['SMA'] = df['Close'].rolling(window=window).mean()

    # محاسبه انحراف معیار
    df['STD'] = df['Close'].rolling(window=window).std()

    # محاسبه نوارهای بولینگر
    df['Bollinger_Upper'] = df['SMA'] + (num_std_dev * df['STD'])
    df['Bollinger_Lower'] = df['SMA'] - (num_std_dev * df['STD'])
    m = [(df['Bollinger_Upper'].iloc[-1]-df['Bollinger_Upper'].iloc[-3])/2,(df['Bollinger_Lower'].iloc[-1]-df['Bollinger_Lower'].iloc[-3])/2]
    # حذف مقادیر اولیه که به دلیل عدم وجود داده کافی NaN هستند
    df = df.dropna()
    return df
