from pathlib import Path
import os

market_his_dir_path = Path(__file__).parent / 'data' / 'marketHistoryData'
bt_data_dir_path = Path(__file__).parent / 'data' / 'backtestData'
ga_his_dir_path = Path(__file__).parent / 'data' / 'gaHistoryData'

for dir_path in [market_his_dir_path, bt_data_dir_path, ga_his_dir_path]:
    if os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Folder {dir_path} not found, creating Folder.")

