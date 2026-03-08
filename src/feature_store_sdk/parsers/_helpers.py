"""
_helpers.py
-----------
Shared helper functions used by multiple category parsers.
"""

import re


def _safe_amount(text):
    """Extract first currency amount from text."""
    m = re.search(r'(?:Rs|INR)\.?\s*([\d,]+(?:\.\d{1,2})?)', text, re.I)
    if m:
        return float(m.group(1).replace(',', ''))
    return None


def _safe_date(text):
    """Extract first date-like string from text."""
    m = re.search(
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{2,4})',
        text, re.I
    )
    return m.group(1).strip() if m else None


def _safe_float(value):
    """Convert a string or numeric value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
