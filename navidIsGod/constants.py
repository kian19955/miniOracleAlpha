from pathlib import Path

market_his_dir_path = Path(__file__).parent / 'data' / 'marketHistoryData'
bt_data_dir_path = Path(__file__).parent / 'data' / 'backtestData'

print(str(bt_data_dir_path) + "test.csv")