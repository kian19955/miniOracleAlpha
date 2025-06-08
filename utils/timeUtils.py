from datetime import datetime, timezone

def seconds_to_next_boundry(interval_seconds: int) -> float:
    """
    Return seconds until the next exact multiple of `interval_seconds`
    since the UNIX epoch (UTC).
    """
    now = datetime.now(timezone.utc).timestamp()
    offset = now % interval_seconds
    return 0.0 if offset == 0.0 else interval_seconds - offset