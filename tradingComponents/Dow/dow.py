import pandas as pd
from scipy.signal import find_peaks

from tradingComponents.Dow.utils.dowEnums import Trend, Phase

# Initialize global variables
last_trend = None
last_trend_time = None


def detect_dow_trend(df: pd.DataFrame):
    """
    Detect market trend based on Dow Theory principles.

    Analyzes price series to identify swing highs and lows, then determines
    if the market is in an uptrend, downtrend, or moving sideways.

    :return: A tuple containing the trend ('TrendInfo: dict', 'Peaks: list', 'Valleys: list'),
    """
    global last_trend, last_trend_time

    price_series = df['Close']

    # Calculate dynamic parameters based on price volatility
    std_dev = price_series.std()
    prominence_val = std_dev * 0.05
    distance_val = 2

    # Find peaks and valleys (keeping this code as requested)
    peaks, _ = find_peaks(price_series, distance=distance_val, prominence=prominence_val)
    valleys, _ = find_peaks(-price_series, distance=distance_val, prominence=prominence_val)

    # Not enough data to determine trend
    if len(peaks) < 2 or len(valleys) < 2:
        return None, peaks, valleys

    # Get the last two peaks and valleys for trend analysis
    highs = [price_series.iloc[peak] for peak in peaks[-2:]]
    lows = [price_series.iloc[valley] for valley in valleys[-2:]]

    # Calculate swing strength
    swing_strength = abs(highs[1] - highs[0]) + abs(lows[1] - lows[0])
    min_swing = std_dev * 0.5

    # Ignore small movements
    if swing_strength < min_swing:
        return None, peaks, valleys

    higher_high = highs[1] > highs[0]
    lower_high = highs[1] < highs[0]
    higher_low = lows[1] > lows[0]
    lower_low = lows[1] < lows[0]

    if higher_high and higher_low:
        trend = Trend.UPTREND
        phase = Phase.ACCUMULATION if higher_low > higher_high else Phase.PARTICIPATION
    elif lower_high and lower_low:
        trend = Trend.DOWNTREND
        phase = Phase.DISTRIBUTION if lower_high > lower_low else Phase.MARKDOWN
    else:
        # Mixed signals
        trend = Trend.SIDEWAYS

        if higher_high and lower_low:
            phase = Phase.CONSOLIDATION_INCREASED_VOLATILITY
        elif lower_high and higher_low:
            phase = Phase.CONSOLIDATION_DECREASED_VOLATILITY
        else:
            phase = Phase.ACCUMULATION

    # Check if trend has changed significantly
    current_time = df.index[-1]
    if last_trend != trend:
        # Require minimum time between trend changes to avoid whipsaws
        if last_trend_time is None or (current_time - last_trend_time).total_seconds() > 3 * 60 * 15:
            last_trend = trend
            last_trend_time = current_time
            print(f"🔔 Trend changed to {trend} ({phase}) at {current_time} | Power: {round(swing_strength, 6)}")

    # Volume confirmation check
    recent_vol = df['Volume'].iloc[-1]
    avg_vol = df['Volume'].rolling(10).mean().iloc[-1]
    vol_ok = recent_vol > avg_vol

    if not vol_ok:
        print("⚠️ Volume too low. Ignoring signal.")
        return None, peaks, valleys

    # Return trend information
    trend_info: dict = {
        'trend': trend,
        'phase': phase,
        'strength': swing_strength,
        'time': current_time,
        'price': df['Close'].iloc[-1]
    }

    return trend_info, peaks, valleys

if __name__ == '__main__':
    """Main function to run the trend detection and plotting"""
    from apis.binanceApi import fetch_klines
    from tradingComponents.Dow.utils import plot_candle_chart

    symbol = 'BTCUSDT'
    # Fetch market data
    df = fetch_klines(
        symbol=symbol,
        interval='1m',
        limit=60
    )
    print(f"Fetched {len(df)} data points for {symbol}")

    # Detect trend
    result, peaks, valleys = detect_dow_trend(df)
    print(peaks)

    # Plot results
    plot_candle_chart(df, peaks, valleys, result, sma=7)

    print(result)


