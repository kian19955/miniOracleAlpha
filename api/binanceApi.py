from typing import Optional
import time
from requests import Response, get
from datetime import datetime, timezone
import os

from pandas import DataFrame, to_datetime, concat, read_csv
from dateutil.relativedelta import relativedelta

from api.utils import handle_binance_status
from constants import market_his_dir_path

url_fetch_ticker_price: str = "https://api.binance.com/api/v3/ticker/price"
url_fetch_klines: str = "https://api.binance.com/api/v3/klines"
url_fetch_exchange_info: str = "https://api.binance.com/api/v3/exchangeInfo"

columns = [
    'OpenTime',
    'Open',
    'High',
    'Low',
    'Close',
    'Volume',
    'CloseTime',
    'QuoteAssetVolume',
    'NumberOfTrades',
    'TakerBuyBaseAssetVolume',
    'TakerBuyQuoteAssetVolume',
    'unused'
]


def fetch_ticker_price(ticker) -> float:
    param: dict = {
        'symbol': ticker
    }
    response: Response = get(url_fetch_ticker_price, params=param)
    data: dict = response.json()

    handle_binance_status(response.status_code, data)

    return float(data["price"])


def fetch_exchange_info() -> dict:
    response: Response = get(url_fetch_exchange_info)

    data: dict = response.json()

    handle_binance_status(response.status_code, data)

    return data


def fetch_klines(
        ticker: str,
        interval: str,
        start: str = None,
        end: str = None,
        years: int = 0,
        months: int = 0,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        use_csv: bool = True
) -> DataFrame:
    """
    Retrieves klines from Binance.

    The time interval is determined as follows:
      - If both start and end are provided, the data from start to end is returned.
      - If end is provided and time interval values (years, months, etc.) are given,
        then start is set to (end - interval).
      - If start is provided and time interval values are given, then end is set to (start + interval).
      - If only start is provided (and no interval values), then end is assumed to be now.
      - If only time interval values are provided (and no start or end), then end is now and
        start is (now - interval).

    :return: DataFrame containing the fetched klines.
    """
    time_format = "%Y-%m-%d %H:%M:%S"

    # Parse provided start and end if any
    start_timestamp = datetime.strptime(start, time_format).replace(tzinfo=timezone.utc) if start else None
    end_timestamp = datetime.strptime(end, time_format).replace(tzinfo=timezone.utc) if end else None

    # Create the time interval (delta) from provided values, if any are nonzero
    if any([years, months, weeks, days, hours, minutes, seconds]):
        delta = relativedelta(years=years, months=months, weeks=weeks,
                              days=days, hours=hours, minutes=minutes, seconds=seconds)
    else:
        delta = None

    if start_timestamp and end_timestamp:
        # Case 1: both provided; ignore delta.
        pass
    elif end_timestamp and not start_timestamp:
        # Case 2: end is provided; use delta to calculate start.
        if delta:
            start_timestamp = end_timestamp - delta
        else:
            raise ValueError("If only end is provided, time intervals must be provided to compute start.")
    elif start_timestamp and not end_timestamp:
        # Case 3: start is provided; use delta to compute end, otherwise end is now.
        if delta:
            end_timestamp = start_timestamp + delta
        else:
            end_timestamp = datetime.now(timezone.utc)
    elif not start_timestamp and not end_timestamp:
        # Case 5: neither provided; must supply delta.
        if delta:
            end_timestamp = datetime.now(timezone.utc)
            start_timestamp = end_timestamp - delta
        else:
            raise ValueError("Either start/end or time interval values must be provided.")

    start_timestamp_unix = int(time.mktime(start_timestamp.timetuple())) * 1000
    end_timestamp_unix = int(time.mktime(end_timestamp.timetuple())) * 1000

    # Create the file path
    safe_start = start.replace(" ", "_").replace(":", "-") if start else 'None'
    safe_end = end.replace(" ", "_").replace(":", "-") if end else 'None'
    file_path = f"{market_his_dir_path}/{ticker}_{interval}_{safe_start}_{safe_end}_{years}Y_{months}M_{weeks}W_{days}D_{hours}h_{minutes}m_{seconds}s.csv"

    if use_csv and os.path.isfile(file_path):
        df: DataFrame = read_csv(file_path)
        df['timestamp'] = to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df

    print(f"{file_path} does not exist. Fetching data from Binance API...")

    df: DataFrame = DataFrame(columns=columns)
    total_time = end_timestamp_unix - start_timestamp_unix
    current_time = start_timestamp_unix

    while current_time < end_timestamp_unix:
        progress = ((current_time - start_timestamp_unix) / total_time) * 100
        print(f"Fetching data... {progress:.2f}% complete", end="\n")

        params: dict = {
            'symbol': ticker,
            'interval': interval,
            'startTime': current_time,
            'endTime': end_timestamp_unix,
            'limit': 1000
        }

        response = get(url_fetch_klines, params=params)
        data = response.json()
        handle_binance_status(response.status_code, data)

        if len(data) == 0:
            break

        new_df: DataFrame = DataFrame(data, columns=columns)
        new_df["timestamp"] = to_datetime(new_df["OpenTime"], unit="ms", utc=True)
        new_df.set_index("timestamp", inplace=True)

        if df.empty:
            df = new_df
        else:
            df = concat([df, new_df])

        current_time = data[-1][6] + 1

    df.drop("unused", axis=1, inplace=True)
    for column in df.columns:
        df[column] = df[column].astype(float)
    df.to_csv(file_path)

    return df


if __name__ == '__main__':
    intervals = "1h"
    days = 7
    tickers = ["BTCUSDT", "DOGEUSDT"]

    for i, ticker in enumerate(tickers):
        print(f"{i + 1}/{len(tickers)}, Fetching {ticker}")
        fetch_klines(ticker, intervals, days=days, use_csv=True)
