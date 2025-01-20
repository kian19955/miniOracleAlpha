import csv
from datetime import datetime


def write_to_csv(data,CSV_FILE):
    """داده‌های جدید را به فایل CSV اضافه می‌کند."""
    file_exists = False
    try:
        file_exists = open(CSV_FILE).read(1) != ""
    except FileNotFoundError:
        pass

    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # اگر فایل وجود نداشت، هدرها را بنویسید
        if not file_exists:
            headers = ["timestamp"] + list(data.keys())
            writer.writerow(headers)

        # داده‌های جدید را اضافه کنید
        row = [datetime.now().isoformat()] + list(data.values())
        writer.writerow(row)