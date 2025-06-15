import time
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

client = Client()

def fetch_klines(symbol: str, interval: str, limit: int, max_retries: int = 5, base_delay: float = 1.0) -> pd.DataFrame:
    """
    Fetches historical kline (candlestick) data from Binance with retry logic.

    Parameters:
    - symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
    - interval (str): Kline interval (e.g., '1m', '5m', '1h').
    - limit (int): Number of data points to retrieve (max 1000).
    - max_retries (int): Maximum number of retries on API failure.
    - base_delay (float): Initial delay between retries (doubles each time).

    Returns:
    - pd.DataFrame: DataFrame containing kline data.
    """
    error: Exception | None = None
    for attempt in range(max_retries):
        try:
            klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
            break  # Success
        except BinanceAPIException as e:
            if e.code == 0 and "503 ERROR" in str(e):
                error = e
                wait = base_delay * (2 ** attempt)
                print(f"[Retry {attempt+1}] Binance CloudFront 503 error. Waiting {wait:.2f}s...")
                time.sleep(wait)
            else:
                raise  # Unhandled error, re-raise
        except BinanceRequestException as e:
            error = e
            wait = base_delay * (2 ** attempt)
            print(f"[Retry {attempt+1}] Network error: {e}. Waiting {wait:.2f}s...")
            time.sleep(wait)
        except Exception as e:
            error = e
            wait = base_delay * (2 ** attempt)
            print(f"[Retry {attempt+1}] Unexpected error: {e}. Waiting {wait:.2f}s...")
            time.sleep(wait)

    else:
        raise error

    # Create DataFrame
    columns = [
        'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close Time', 'Quote Asset Volume', 'Number of Trades',
        'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore'
    ]
    df = pd.DataFrame(klines, columns=columns)

    # Drop unused column
    df = df.drop(columns=['Ignore'])

    # Convert timestamp columns
    df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
    df['Close Time'] = pd.to_datetime(df['Close Time'], unit='ms')
    df.set_index('Open Time', inplace=True)

    # Convert price and volume to float
    float_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[float_cols] = df[float_cols].astype(float)

    return df
