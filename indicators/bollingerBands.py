import pandas as pd

def bollinger_bands(df, window, bbw_min=0.02, bbw_max=0.5):
    """
    محاسبه نوارهای بولینگر و سیگنال نرمال‌شده BBW
    Args:
        df (DataFrame): دیتافریم ورودی شامل ستون 'Close'
        window (int): بازه برای میانگین متحرک و انحراف معیار
        bbw_min (float): حداقل BBW برای نرمال‌سازی
        bbw_max (float): حداکثر BBW برای نرمال‌سازی
    Returns:
        DataFrame: دیتافریم شامل Bollinger Bands و سیگنال
    """
    num_std_dev = 2  # تعداد انحراف معیار

    # محاسبه SMA و انحراف معیار
    df['SMA'] = df['Close'].rolling(window=window).mean()
    df['STD'] = df['Close'].rolling(window=window).std()

    # محاسبه نوارهای بولینگر
    df['Bollinger_Upper'] = df['SMA'] + (num_std_dev * df['STD'])
    df['Bollinger_Lower'] = df['SMA'] - (num_std_dev * df['STD'])

    # محاسبه Bollinger Band Width (BBW)
    df['BBW'] = (df['Bollinger_Upper'] - df['Bollinger_Lower'])/  df['SMA']

    # محاسبه سیگنال نرمال‌شده
    df['BBW_Normalized'] = (df['BBW'] - bbw_min) / (bbw_max - bbw_min)
    df['BBW_Normalized'] = 1 - df['BBW_Normalized']  # معکوس‌سازی برای سیگنال

    # محدود کردن سیگنال به [0, 1]
    df['BBW_Normalized'] = df['BBW_Normalized'].clip(0, 1)

    # حذف مقادیر NaN
    df = df.dropna()

    return df