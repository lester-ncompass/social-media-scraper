import re
from datetime import datetime, timedelta


def time_to_epoch(s: str) -> int:
    """
    Convert a given time string to its equivalent epoch timestamp.

    The function supports various types of input strings:
    1. Relative time with units (e.g., "1m" for one minute ago, "3h" for three hours ago, "2d" for two days ago).
    2. Absolute date with abbreviated or full month name (e.g., "Jun 18, 2024" or "June 18, 2024").
    3. Full datetime in the format "YYYY-MM-DD HH:MM:SS" (e.g., "2025-07-06 12:47:20").
    4. ISO 8601 datetime in the format "YYYY-MM-DDTHH:MM:SS.SSSZ" (e.g., "2025-07-18T01:00:12.000Z").
    5. Date with month name and time (e.g. "July 9 at 3:10 am" or "29 June at 18:23").
    6. Month and day only, assuming the current year (e.g., "May 23", "28 March").

    Args:
        s (str): The time string to convert.

    Returns:
        int: The equivalent epoch timestamp.

    Raises:
        ValueError: If the input string is in an unrecognized format or contains an unknown time unit.
    """  # noqa

    now = datetime.now()

    # Handle relative time (e.g. "1m", "3h", "2d")
    rel_match = re.match(r"(\d+)([mhd])$", s)
    if rel_match:
        value, unit = rel_match.groups()
        value = int(value)
        if unit == "m":
            dt = now - timedelta(minutes=value)
        elif unit == "h":
            dt = now - timedelta(hours=value)
        elif unit == "d":
            dt = now - timedelta(days=value)
        else:
            raise ValueError(f"Unknown time unit: {unit}")
        return int(dt.timestamp())

    # Try parsing absolute date with abbreviated or full month name (e.g., "Jun 18, 2024" or "June 18, 2024")  # noqa
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return int(dt.timestamp())
        except ValueError:
            continue

    # Try parsing date with month name and time (e.g. "July 9 at 3:10 am")
    try:
        dt = datetime.strptime(s + ", " + str(now.year), "%B %d at %I:%M %p, %Y")
        return int(dt.timestamp())
    except ValueError:
        pass

    # Try parsing date with month name and time (e.g. "29 June at 18:23")
    for fmt in ("%d %B at %H:%M", "%d %B at %I:%M %p"):
        try:
            dt = datetime.strptime(s, fmt)
            dt = dt.replace(year=now.year)
            return int(dt.timestamp())
        except ValueError:
            continue

    # Handle full datetime like "2025-07-06 12:47:20"
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp())
    except ValueError:
        pass

    # Handle ISO 8601 datetime like "2025-07-18T01:00:12.000Z"
    try:
        dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ")
        return int(dt.timestamp())
    except ValueError:
        pass

    # Handle month and day only, assuming the current year (e.g., "May 23")
    try:
        dt = datetime.strptime(s + f" {now.year}", "%B %d %Y")
        return int(dt.timestamp())
    except ValueError:
        pass

    # Handle day and month only, assuming the current year (e.g., "28 March")
    try:
        dt = datetime.strptime(s, "%d %B")
        dt = dt.replace(year=now.year)
        return int(dt.timestamp())
    except ValueError:
        pass

    raise ValueError(f"Unrecognized date format: {s}")
