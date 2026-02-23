import pandas as pd
import os
import re

# -----------------------------
# Offer/Marketing guard
# -----------------------------
_OFFER_PATTERNS = [
    r"\bpre[-\s]?qualified\b",
    r"\bpre[-\s]?approved\b",
    r"\bapproved\s+for\b",
    r"\byou('?re| are)\s+eligible\b",
    r"\bapply\s+now\b",
    r"\binstant\s+approval\b",
    r"\bclick\s+(now|here)\b",
    r"\boffer\b",
    r"\boffer\s+valid\b",
    r"\bvalid\s+till\b",
    r"\bzero\s+joining\s+fee\b",
    r"\bjoining\s+fee\b",
    r"\bannual\s+fee\b",
    r"\bannual\s+cashback\b",
    r"\bcashback\b",
    r"\bcredit\s+limit\b",
    r"\blimit\s+of\s+up\s+to\b",
    r"\bcard\b.*\b(offer|eligible|pre[-\s]?approved|pre[-\s]?qualified|apply)\b",
]

# If these appear, it becomes *very likely* it's NOT a transaction
_NON_TXN_STRONG_CTA = [
    r"\bhttp\b", r"\bwww\b", r"\bclick\b", r"\bapply\b", r"\bavail\b", r"\boffer\s+valid\b"
]


def is_offer_or_marketing(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    t = text.lower()

    # must NOT be an actual txn indicator
    txn_verbs = re.search(r"\b(credited|debited|spent|paid|purchase|withdrawn|received|transferred)\b", t)
    if txn_verbs:
        # if txn verbs exist, only block if BOTH strong offer cues AND strong CTA are present
        strong_offer = any(re.search(p, t) for p in _OFFER_PATTERNS)
        strong_cta   = any(re.search(p, t) for p in _NON_TXN_STRONG_CTA)
        return bool(strong_offer and strong_cta)

    # no txn verbs -> if any offer marker appears, classify as offer
    return any(re.search(p, t) for p in _OFFER_PATTERNS)

def extract_limit(text):
    if not isinstance(text, str):
        return None
    pattern = r"(?i)(?:limit|up to|upto|approved|sanctioned|loan|cash|rs\.?|inr)\s*(?:of\s*)?(?:rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)"
    m = re.search(pattern, text)
    if not m:
        return None

    amt = m.group(1).replace(",", "")
    try:
        return float(amt)
    except:
        return None

def get_promotion_stats(promo_df):
    """Returns promotional stats as a structured dict."""
    promo_df = promo_df.copy()

    re_cc      = re.compile(r"(?i)credit\s*card|cc\b")
    re_lending  = re.compile(r"(?i)loan|lending|nbfc|credit\s*line|instant\s*cash|personal\s*loan")

    promo_df['is_cc']      = promo_df['body'].str.contains(re_cc, na=False)
    promo_df['is_offer']   = promo_df['body'].apply(is_offer_or_marketing)
    promo_df['is_lending'] = promo_df['body'].str.contains(re_lending, na=False)
    promo_df['is_other'] = ~(promo_df['is_cc'] | promo_df['is_offer'] | promo_df['is_lending'])
    promo_df['extracted_limit'] = promo_df['body'].apply(extract_limit)

    cc_limits = promo_df[promo_df['is_cc'] & promo_df['extracted_limit'].notnull()]['extracted_limit'].tail(5)
    lending_limits = promo_df[promo_df['is_lending'] & promo_df['extracted_limit'].notnull()]['extracted_limit'].tail(5)

    return {
        "total_promotional_messages": len(promo_df),
        "credit_card_messages": int(promo_df['is_cc'].sum()),
        "offer_or_discount_messages": int(promo_df['is_offer'].sum()),
        "lending_app_messages": int(promo_df['is_lending'].sum()),
        "other_messages": int(promo_df['is_other'].sum()),
        "avg_last5_cc_limit": round(float(cc_limits.mean()), 2) if not cc_limits.empty else 0.0,
        "avg_last5_lending_limit": round(float(lending_limits.mean()), 2) if not lending_limits.empty else 0.0,
    }

def analyze_promotions(df):
    """
    Analyzes SMS dataframe to separate promotional messages (address ends with -P) 
    and returns promo_df, rest_df, and stats.
    """
    if 'address' not in df.columns or 'body' not in df.columns:
        print("Required columns ('address' or 'body') not found in the Dataframe.")
        return pd.DataFrame(), df, "No promo analysis: missing columns"

    # Separate Promotional vs Rest
    mask_promo = df['address'].str.endswith('-P', na=False)
    promo_df = df[mask_promo]
    rest_df = df[~mask_promo]

    # Generate stats report string
    report_dict = get_promotion_stats(promo_df)
    
    return promo_df, rest_df, report_dict

if __name__ == "__main__":
    input_data_path = r"d:\Sign3Project\Regex Notebooks\sms_parsing_input_data.csv"
    analyze_promotions(input_data_path)
