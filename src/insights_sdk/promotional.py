"""
promotional.py
--------------
Promotional insights generator. Self-contained.
"""

import re

import pandas as pd

from .utils import r2


def extract_limit(text):
    """Extract a monetary limit from promotional SMS text."""
    if not isinstance(text, str):
        return None
    pattern = r"(?i)(?:limit|up to|upto|approved|sanctioned|loan|cash|rs\.?|inr)\s*(?:of\s*)?(?:rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)"
    m = re.search(pattern, text)
    if not m:
        return None
    amt = m.group(1).replace(",", "")
    try:
        return float(amt)
    except Exception:
        return None


def generate_promotional_insights(feature_store: list[dict]) -> dict | None:
    """Generate promotional insights from the feature store.

    Filters for sms_category == 'Promotions', computes stats,
    and outputs the final shape (merged fmt_promotional).
    """
    promo_dicts = [d for d in feature_store if d.get("sms_category") == "promotions"]
    if not promo_dicts:
        return None

    # Build a DataFrame for vectorized classification
    promo_df = pd.DataFrame(promo_dicts)

    # Use raw_body as the text field
    body_col = "raw_body"
    if body_col not in promo_df.columns:
        return None

    re_cc = re.compile(r"(?i)credit\s*card|cc\b")
    re_lending = re.compile(r"(?i)loan|lending|nbfc|credit\s*line|instant\s*cash|personal\s*loan")

    # Offer detection patterns
    _OFFER_PATTERNS = [
        r"\bpre[-\s]?qualified\b", r"\bpre[-\s]?approved\b", r"\bapproved\s+for\b",
        r"\byou('?re| are)\s+eligible\b", r"\bapply\s+now\b", r"\binstant\s+approval\b",
        r"\bclick\s+(now|here)\b", r"\boffer\b", r"\boffer\s+valid\b", r"\bvalid\s+till\b",
        r"\bzero\s+joining\s+fee\b", r"\bjoining\s+fee\b", r"\bannual\s+fee\b",
        r"\bannual\s+cashback\b", r"\bcashback\b", r"\bcredit\s+limit\b",
        r"\blimit\s+of\s+up\s+to\b",
        r"\bcard\b.*\b(offer|eligible|pre[-\s]?approved|pre[-\s]?qualified|apply)\b",
    ]

    def _is_offer(text):
        if not isinstance(text, str) or not text.strip():
            return False
        t = text.lower()
        return any(re.search(p, t) for p in _OFFER_PATTERNS)

    promo_df["is_cc"] = promo_df[body_col].str.contains(re_cc, na=False)
    promo_df["is_offer"] = promo_df[body_col].apply(_is_offer)
    promo_df["is_lending"] = promo_df[body_col].str.contains(re_lending, na=False)
    promo_df["is_other"] = ~(promo_df["is_cc"] | promo_df["is_offer"] | promo_df["is_lending"])
    promo_df["extracted_limit"] = promo_df[body_col].apply(extract_limit)

    cc_limits = promo_df[promo_df["is_cc"] & promo_df["extracted_limit"].notnull()]["extracted_limit"].tail(5)
    lending_limits = promo_df[promo_df["is_lending"] & promo_df["extracted_limit"].notnull()]["extracted_limit"].tail(5)

    return {
        "total_messages": len(promo_df),
        "breakdown": {
            "credit_card": int(promo_df["is_cc"].sum()),
            "offer_or_discount": int(promo_df["is_offer"].sum()),
            "lending_app": int(promo_df["is_lending"].sum()),
            "other": int(promo_df["is_other"].sum()),
        },
        "avg_limit_offers": {
            "credit_card_last5": r2(float(cc_limits.mean())) if not cc_limits.empty else 0,
            "lending_app_last5": r2(float(lending_limits.mean())) if not lending_limits.empty else 0,
        },
    }
