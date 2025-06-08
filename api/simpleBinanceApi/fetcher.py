import time

from binance.client import Client
import pandas as pd

def fetch_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    """
    Fetches historical kline (candlestick) data from Binance.

    Parameters:
    - symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
    - interval (str): Kline interval (1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M).
    - limit (int): Number of data points to retrieve (max 1000).

    Returns:
    - pd.DataFrame: DataFrame containing open time, open, high, low, close, volume, etc.
    """
    # Initialize Binance client (no API key required for public data)
    client = Client()

    # Fetch klines
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

    # Define column names as per Binance API documentation
    columns = [
        'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close Time', 'Quote Asset Volume', 'Number of Trades',
        'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore'
    ]

    # Create DataFrame
    df = pd.DataFrame(klines, columns=columns)
    df.drop(columns=['Ignore'])

    # Convert 'Open Time' and 'Close Time' to datetime and set as index
    df['Close Time'] = pd.to_datetime(df['Close Time'], unit='ms')
    df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
    df.set_index('Open Time', drop=False)

    # Convert price and volume columns to float
    numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[numeric_columns] = df[numeric_columns].astype(float)

    return df

if __name__ == '__main__':
    df1 = fetch_klines(symbol='BTCUSDT', interval='1m', limit=1)
    df2 = fetch_klines(symbol='BTCUSDT', interval='1m', limit=1)
    print(df1.iloc[-1]['Open Time'] == df2.iloc[-1]['Open Time'])
