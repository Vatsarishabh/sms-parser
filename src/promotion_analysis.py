import pandas as pd
import os
import re

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

    re_cc = re.compile(r"(?i)credit\s*card|cc\b")
    re_offer = re.compile(r"(?i)offer|discount|%\s*off|save\b")
    re_lending = re.compile(r"(?i)loan|lending|nbfc|credit\s*line|instant\s*cash|personal\s*loan")

    promo_df['is_cc'] = promo_df['body'].str.contains(re_cc, na=False)
    promo_df['is_offer'] = promo_df['body'].str.contains(re_offer, na=False)
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
