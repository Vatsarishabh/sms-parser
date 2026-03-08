"""
utils.py
--------
Shared utilities for the insights_sdk package.
"""

import math
from datetime import datetime, timezone


def sanitize(obj, strip_nulls: bool = True):
    """Recursively convert NaN/Inf/Timestamps/numpy scalars to JSON-safe types.

    When strip_nulls is True (default), keys with None values are removed from dicts.
    Floats are rounded to 2dp. Booleans are preserved. numpy scalars are
    converted to native Python types.
    """
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            val = sanitize(v, strip_nulls)
            if strip_nulls and val is None:
                continue
            cleaned[k] = val
        return cleaned
    if isinstance(obj, list):
        return [sanitize(i, strip_nulls) for i in obj]
    # bool must be checked before int (bool is subclass of int)
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return round(obj, 2)
    if isinstance(obj, int):
        return obj
    if hasattr(obj, "isoformat"):
        return str(obj)
    if hasattr(obj, "item"):
        # numpy scalar → Python native, then re-sanitize for type consistency
        return sanitize(obj.item(), strip_nulls)
    return obj


def r2(val, fallback=None):
    """Round to 2 dp; return fallback if None/NaN."""
    try:
        if val is None or math.isnan(float(val)):
            return fallback
        return round(float(val), 2)
    except Exception:
        return fallback


def parse_timestamp(value) -> datetime | None:
    """Parse a timestamp value into a datetime object.

    Handles:
      - None / empty string -> None
      - datetime object -> returned as-is
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
