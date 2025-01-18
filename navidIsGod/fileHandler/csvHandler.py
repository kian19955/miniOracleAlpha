from typing import Optional
import csv
from datetime import datetime


from navidIsGod.config import rel_data_dir_path

def write_to_csv(
        headers: list[str],
        data: list[list[str | int | float]],
        filename: Optional[str] = None,
        append: bool = False,
) -> None:
    """
    Save data to a CSV file. For headers, the keys of the dictionary are used.

    :param headers: The headers of the CSV file.
    :param data: The data to save.
    :param filename: The name of the file to save to.
    :param append: If True, append to the file.
    """
    if filename is None:
        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".csv"
    elif not filename.endswith(".csv"):
        filename += ".csv"

    file_path = rel_data_dir_path + filename

    mode: str = "a" if append else "w"

    with open(file_path, mode=mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not append:
            writer.writerow(headers)

        writer.writerows(data)


def read_from_csv(filename: str) -> list[list[str | int | float]]:
    file_path = rel_data_dir_path + filename

    if not file_path.endswith(".csv"):
        file_path += ".csv"

    with open(file_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return list(reader)