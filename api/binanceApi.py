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


def fetch_exchange_info(tickers: Optional[list[str]] = None) -> dict:
    response: Response = get(url_fetch_exchange_info)

    data: dict = response.json()

    handle_binance_status(response.status_code, data)

    return data


def fetch_klines(
        ticker: str,
        interval: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        years: int = 0,
        months: int = 0,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        use_csv: bool = True
):
    """
    Retrieves klines from Binance

    :param ticker: The ticker of the asset
    :param interval: The interval of the klines ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    :param start: The start time in the format 'YYYY-MM-DD HH:MM:SS'
    :param end: The end time in the format 'YYYY-MM-DD HH:MM:SS'
    :param years: The number of years to go back
    :param months: The number of months to go back
    :param weeks: The number of weeks to go back
    :param days: The number of days to go back
    :param hours: The number of hours to go back
    :param minutes: The number of minutes to go back
    :param seconds: The number of seconds to go back
    :param use_csv: Whether to load data from saved csv if available, else it will overwrite if such file exists
    :return: DataFrame
    """
    if end is not None and start is None:
        raise ValueError("start_time cannot be specified without start_time")

    if end is None and all(v == 0 for v in [years, months, days, weeks, hours, minutes, seconds]):
        raise ValueError(
            "end_time must be specified or any of years, months, days, hours, or minutes should be provided to calculate it")

    if end is not None and start is None and all(v == 0 for v in [years, months, weeks, days, hours, minutes, seconds]):
        raise ValueError(
            "If end_time is provided, either end_time or a time difference (years, months, etc.) must be provided")

    file_path = f"{market_his_dir_path}/{ticker}_{days}_{interval}.csv"
    if not os.path.isfile(file_path):
        print(f"{file_path} does not exist. Fetching data from Binance API...")
        use_csv = False

    if use_csv:
        df: DataFrame = read_csv(f"{market_his_dir_path}/{ticker}_{days}_{interval}.csv")
        df['timestamp'] = to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        return df

    time_format = "%Y-%m-%d %H:%M:%S"

    if end is not None:
        end_timestamp: datetime = datetime.strptime(end, time_format)
        end_timestamp = end_timestamp.replace(tzinfo=timezone.utc)
    else:
        end_timestamp: datetime = datetime.now(timezone.utc)

    if start is not None:
        start_timestamp: datetime = datetime.strptime(start, time_format)
        start_timestamp = start_timestamp.replace(tzinfo=timezone.utc)
    else:
        start_timestamp: datetime = end_timestamp - relativedelta(
            years=years,
            months=months,
            weeks=weeks,
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds
        )

    # Convert to UNIX timestamp
    start_timestamp_unix: int = int(time.mktime(start_timestamp.timetuple())) * 1000
    end_timestamp_unix: int = int(time.mktime(end_timestamp.timetuple())) * 1000

    df: DataFrame = DataFrame(columns=columns)

    total_time = end_timestamp_unix - start_timestamp_unix
    current_time = start_timestamp_unix

    while current_time < end_timestamp_unix:
        # Calculate progress percentage
        progress = ((current_time - start_timestamp_unix) / total_time) * 100
        print(f"Fetching data... {progress:.2f}% complete")

        params: dict = {
            'symbol': ticker,
            'interval': interval,
            'startTime': current_time,
            'endTime': end_timestamp_unix,
            'limit': 1000
        }

        response: Response = get(url_fetch_klines, params=params)

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

        # Update current_time to the end of the current batch
        current_time = data[-1][6] + 1

    df.drop("unused", axis=1, inplace=True)

    for column in df.columns:
        df[column] = df[column].astype(float)

    df.to_csv(f"{market_his_dir_path}/{ticker}_{days}_{interval}.csv")

    print("Data fetching complete!")
    return df


if __name__ == '__main__':
    intervals = "1s"
    days = 7
    tickers = ["BTCUSDT", "DOGEUSDT"]

    for i, ticker in enumerate(tickers):
        print(f"{i+1}/{len(tickers)}, Fetching {ticker}")
        fetch_klines(ticker, intervals, days = days, use_csv=True)