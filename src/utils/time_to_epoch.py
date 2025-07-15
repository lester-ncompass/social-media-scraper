from datetime import datetime, timedelta
import re


def time_to_epoch(s: str) -> int:
    """
    Convert a given time string to its equivalent epoch timestamp.

    The function supports various types of input strings:
    1. Relative time with units (e.g., "1m" for one minute ago, "3h" for three hours ago, "2d" for two days ago).
    2. Absolute date with abbreviated or full month name (e.g., "Jun 18, 2024" or "June 18, 2024").
    3. Full datetime in the format "YYYY-MM-DD HH:MM:SS" (e.g., "2025-07-06 12:47:20").
    4. Date with month name and time (e.g. "July 9 at 3:10 am").
    5. Month and day only, assuming the current year (e.g., "May 23").

    Args:
        s (str): The time string to convert.

    Returns:
        int: The equivalent epoch timestamp.

    Raises:
        ValueError: If the input string is in an unrecognized format or contains an unknown time unit.
    """

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

    # Try parsing absolute date with abbreviated or full month name (e.g., "Jun 18, 2024" or "June 18, 2024")
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

    # Handle full datetime like "2025-07-06 12:47:20"
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp())
    except ValueError:
        pass

    # Handle month and day only, assuming the current year (e.g., "May 23")
    try:
        dt = datetime.strptime(s + f" {now.year}", "%B %d %Y")
        return int(dt.timestamp())
    except ValueError:
        pass

    raise ValueError(f"Unrecognized date format: {s}")
