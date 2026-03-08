"""
insurance.py
------------
Insurance insights generator. Self-contained.
"""

import re

import pandas as pd

from .utils import parse_timestamp, r2


def clean_insurance_names(raw_list):
    """Normalize and deduplicate beneficiary names extracted from insurance SMS."""
    noise_phrases = [
        r'on behalf of.*', r'thank you for choosing.*', r'niva bupa.*',
        r'we hope this message.*', r'your policy is now active.*', r' Mam$', r' Mamta$',
    ]
    cleaned_names = []
    for text in raw_list:
        if not text:
            continue
        name = re.sub(r'^(mr\.|ms\.|mrs\.|dear|mr|ms|dr\.)\s?', '', text.lower()).strip()
        for phrase in noise_phrases:
            name = re.sub(phrase, '', name, flags=re.I).strip()
        name = re.sub(r'[.\W_]+$', '', name).strip()
        if len(name) > 3:
            cleaned_names.append(name)

    cleaned_names = sorted(list(set(cleaned_names)), key=len, reverse=True)
    final_unique = []
    for name in cleaned_names:
        if not any(name in existing for existing in final_unique):
            final_unique.append(name)
    return [n.title() for n in final_unique]


def generate_insurance_insights(feature_store: list[dict]) -> dict | None:
    """Generate insurance insights from the feature store.

    Filters for sms_category == 'Insurance', runs the full insurance
    analysis pipeline, and outputs the final shape (merged fmt_insurance).
    """
    parsed_dicts = [d for d in feature_store if d.get("sms_category") == "insurance"]
    if not parsed_dicts:
        return None

    date_col = "timestamp"
    ins_df = pd.DataFrame(parsed_dicts)

    # Ensure expected columns exist (null-stripped dicts may omit them)
    for col in ("insurer_name", "premium_amount", "policy_number", "event_type",
                "insurance_type", "raw_body", date_col):
        if col not in ins_df.columns:
            ins_df[col] = None

    # Filter rows where insurer_name is present
    ins_df = ins_df[ins_df["insurer_name"].notna()].copy()
    if ins_df.empty:
        return None

    # Ensure date context
    if not pd.api.types.is_datetime64_any_dtype(ins_df[date_col]):
        ins_df[date_col] = ins_df[date_col].apply(lambda v: parse_timestamp(v))
        ins_df[date_col] = pd.to_datetime(ins_df[date_col], errors="coerce")

    if ins_df.empty or ins_df[date_col].isna().all():
        return None

    # --- 1. Basic Metrics ---
    ins_df["premium_amount"] = ins_df["premium_amount"].fillna(0)
    has_policy = ins_df["policy_number"].notna()
    total_premium = (
        ins_df.loc[has_policy].groupby("policy_number")["premium_amount"].max().sum()
        if has_policy.any()
        else ins_df["premium_amount"].sum()
    )
    wellness_count = len(ins_df[ins_df["event_type"] == "wellness"])
    wei_score = (wellness_count / len(ins_df)) * 100 if len(ins_df) > 0 else 0

    # --- 2. Household & Name Normalization ---
    name_pattern = r'(?:Dear\s?)(Mr\.|Ms\.)\s?([A-Za-z\s\.]+?)(?=\s(?:on|we|your|would))'
    raw_names = ins_df["raw_body"].apply(
        lambda x: re.search(name_pattern, str(x)).group(2).strip()
        if re.search(name_pattern, str(x)) else None
    ).dropna().tolist()
    final_household = clean_insurance_names(raw_names)
    household_count = len(final_household)

    # --- 3. Quarter Liability Density ---
    ins_df["quarter"] = ins_df[date_col].dt.quarter
    q_burn = ins_df.groupby("quarter")["premium_amount"].sum()
    peak_quarter = f"Q{q_burn.idxmax()}" if not q_burn.empty and not pd.isna(q_burn.idxmax()) else "N/A"

    # --- 4. Premium Concentration Index (PCI) ---
    max_single_premium = ins_df["premium_amount"].max()
    pci_score = (max_single_premium / total_premium * 100) if total_premium > 0 else 0

    # --- 5. Protection Balance Ratio ---
    mix = ins_df["insurance_type"].value_counts()
    health_count = mix.get("health", 0)
    life_count = mix.get("life", 0)
    health_vs_life = health_count / life_count if life_count > 0 else (health_count if health_count > 0 else 0)

    # --- Final output in the target shape ---
    return {
        "coverage": {
            "total_premium_liability": r2(float(total_premium)),
            "peak_liability_quarter": peak_quarter,
            "premium_concentration_index": r2(float(pci_score)),
        },
        "household": {
            "size": int(household_count),
            "avg_cost_per_member": r2(float(total_premium) / household_count) if household_count > 0 else 0,
        },
        "engagement": {
            "wellness_index_pct": r2(float(wei_score)),
            "health_to_life_ratio": r2(float(health_vs_life)),
        },
    }
