import re
import warnings


def parse_interval(interval: str) -> int:
    """
    Converts a Binance kline interval string to its duration in seconds.

    Parameters:
    - interval (str): The kline interval (e.g., '1m', '3h', '1d').

    Returns:
    - int: The duration of the interval in seconds.

    Raises:
    - ValueError: If the interval is not recognized.
    """
    # Define a mapping of units to their corresponding durations in seconds
    unit_to_seconds = {
        's': 1,        # seconds
        'm': 60,       # minutes
        'h': 3600,     # hours
        'd': 86400,    # days
        'w': 604800,   # weeks
        'M': 2592000   # months (approximated as 30 days)
    }

    # Use regular expression to extract the numeric part and the unit
    match = re.match(r"(\d+)([smhdwM])", interval)
    if not match:
        raise ValueError(f"Invalid interval format: {interval}")

    # Extract the numeric part and the unit
    quantity, unit = match.groups()
    quantity = int(quantity)

    # Check if the unit is valid and calculate the duration in seconds
    if unit in unit_to_seconds:
        if unit == 'M':
            warnings.warn("Approximating months as 30 days.", UserWarning)
        return quantity * unit_to_seconds[unit]
    else:
        raise ValueError(f"Unsupported unit: {unit}")
