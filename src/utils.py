"""
utils.py
--------
Shared utilities for the SMS parser pipeline.
"""

from datetime import datetime, timezone


def parse_timestamp(value) -> datetime | None:
    """Parse a timestamp value into a datetime object.

    Handles:
      - None / empty string → None
      - datetime object → returned as-is
      - int/float epoch milliseconds (> 1e12)
      - int/float epoch nanoseconds (> 1e18)
      - int/float epoch seconds (> 1e9)
      - ISO-8601 and common date strings
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    # Handle pandas Timestamp objects
    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime().replace(tzinfo=None)
        except Exception:
            return None

    # Numeric epochs (always return tz-naive UTC for consistency)
    if isinstance(value, (int, float)):
        try:
            if value > 1e18:
                return datetime.fromtimestamp(value / 1e9, tz=timezone.utc).replace(tzinfo=None)
            if value > 1e12:
                return datetime.fromtimestamp(value / 1e3, tz=timezone.utc).replace(tzinfo=None)
            if value > 1e9:
                return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
        except (OSError, ValueError, OverflowError):
            return None
        return None

    # String values
    s = str(value).strip()
    if not s or s.lower() in ("none", "nan", "nat", ""):
        return None

    # Try numeric string (epoch)
    try:
        num = float(s)
        return parse_timestamp(num)
    except ValueError:
        pass

    # Common datetime string formats (ordered most-specific first)
    _FORMATS = [
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]
    for fmt in _FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=None)
        except ValueError:
            continue

    return None
