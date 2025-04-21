import numpy as np
from pandas import Series
from scipy.signal import argrelextrema


def detect_support_resistance(price_data, order=15):
    local_max = argrelextrema(price_data['Close'].values, np.greater_equal, order=order)[0]
    local_min = argrelextrema(price_data['Close'].values, np.less_equal, order=order)[0]

    resistance = price_data.iloc[local_max]['Close'].values
    support = price_data.iloc[local_min]['Close'].values

    return support, resistance

def get_nearest_levels(close_price, support_levels, resistance_levels):
    nearest_support = max([level for level in support_levels if level < close_price], default=None)
    nearest_resistance = min([level for level in resistance_levels if level > close_price], default=None)
    return nearest_support, nearest_resistance

def check_breakout(last_close, nearest_support, nearest_resistance, close_time) -> dict[str, float | str]:
    breakout_info: dict[str, float | str] = {
        'support': nearest_support,
        'resistance': nearest_resistance,
        'direction': None,
        'price': last_close,
        'time': close_time
    }

    if nearest_support and last_close < nearest_support:
        breakout_info['direction'] = 'below'
    elif nearest_resistance and last_close > nearest_resistance:
        breakout_info['direction'] = 'above'

    return breakout_info

def breakout(df) -> dict[str, float | str]:
    support, resistance = detect_support_resistance(df.iloc[:-1], order=4)
    last_candle: Series = df.iloc[-2]  # کندل بسته‌شده‌ی آخر
    last_close: float = last_candle['Close']
    close_time: str = last_candle['Close Time']

    nearest_support, nearest_resistance = support[-1], resistance[-1]
    breakouts: dict[str, float | str] = check_breakout(last_close, nearest_support, nearest_resistance, close_time)
    return breakouts