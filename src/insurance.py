import re
import pandas as pd

from src.models import InsuranceParsed
from src.utils import parse_timestamp


def parse_insurance_model(body, address, base_fields=None):
    """Parse a single insurance SMS into an InsuranceParsed dataclass instance.

    Parameters
    ----------
    body : str
        The raw SMS body text.
    address : str
        The sender address / phone number.
    base_fields : dict, optional
        Pre-computed SMSBase fields to populate on the returned dataclass.

    Returns
    -------
    InsuranceParsed
        A dataclass instance with extracted insurance features.
    """
    msg = str(body) if body else ""

    # --- Insurer name & insurance type ---
    insurer_name = None
    insurance_type = None
    if "Niva Bupa" in msg:
        insurer_name = "Niva Bupa"
        insurance_type = "Health"
    elif "LIC" in msg:
        insurer_name = "LIC"
        insurance_type = "Life"

    # --- Event type ---
    event_type = None
    msg_lower = msg.lower()
    if "renewed" in msg_lower or "renewal" in msg_lower:
        event_type = "Renewal"
    elif "due" in msg_lower:
        event_type = "Premium Due"
    elif "active" in msg_lower:
        event_type = "New Policy"
    elif "health check-up" in msg_lower:
        event_type = "Wellness"
    elif "Survival Benefit" in msg:
        event_type = "Payout"

    # --- Policy number ---
    policy_number = None
    policy_match = re.search(r'Policy\s?No\.?\s?(\d+)', msg, re.I)
    if policy_match:
        policy_number = policy_match.group(1)

    # --- Premium amount ---
    premium_amount = None
    amt_match = re.search(r'Rs\.?\s?\**(\d+\.?\d*)', msg)
    if amt_match:
        premium_amount = float(amt_match.group(1))

    # --- Beneficiary name ---
    beneficiary_name = None
    name_match = re.search(
        r'Dear\s?(Mr\.|Ms\.)\s?([A-Za-z\s\.]+?)(?=\s(?:on|we|your|would))',
        msg,
    )
    if name_match:
        beneficiary_name = name_match.group(2).strip()

    # --- Date extraction helper ---
    date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{2,4})'

    # --- Due date ---
    due_date = None
    due_date_match = re.search(date_pattern, msg, re.I)
    if due_date_match:
        due_date = due_date_match.group(1).strip()

    # --- Renewal date (date appearing near "renewal" / "renew") ---
    renewal_date = None
    renewal_region = re.search(
        r'(?:renew(?:al|ed)?).{0,40}?' + date_pattern,
        msg,
        re.I,
    )
    if renewal_region:
        renewal_date = renewal_region.group(1).strip()

    # --- Build kwargs for the dataclass ---
    kwargs = dict(
        raw_body=msg,
        sender_address=str(address) if address else "",
        insurer_name=insurer_name,
        insurance_type=insurance_type,
        event_type=event_type,
        policy_number=policy_number,
        premium_amount=premium_amount,
        beneficiary_name=beneficiary_name,
        due_date=due_date,
        renewal_date=renewal_date,
    )

    # Overlay any pre-computed base fields
    if base_fields and isinstance(base_fields, dict):
        for key, value in base_fields.items():
            kwargs.setdefault(key, value)

    return InsuranceParsed(**kwargs)


def generate_insurance_insights(parsed_dicts, date_col='timestamp'):
    """Generate insurance insights from a list of InsuranceParsed dicts.

    Parameters
    ----------
    parsed_dicts : list[dict]
        List of dicts produced by ``InsuranceParsed.to_dict()``.
    date_col : str, optional
        Name of the timestamp column in each dict (default ``'timestamp'``).

    Returns
    -------
    dict or None
        A dictionary of computed insurance metrics, or ``None`` if there
        are no valid insurance rows.
    """
    if not parsed_dicts:
        return None

    ins_df = pd.DataFrame(parsed_dicts)

    # Filter rows where insurer_name is present
    ins_df = ins_df[ins_df['insurer_name'].notna()].copy()
    if ins_df.empty:
        return None

    # Ensure date context — handles epoch ms/ns/s and string formats
    if not pd.api.types.is_datetime64_any_dtype(ins_df[date_col]):
        ins_df[date_col] = ins_df[date_col].apply(lambda v: parse_timestamp(v))
        ins_df[date_col] = pd.to_datetime(ins_df[date_col], errors='coerce')

    if ins_df.empty or ins_df[date_col].isna().all():
        return None

    # --- 1. Basic Metrics ---
    ins_df['premium_amount'] = ins_df['premium_amount'].fillna(0)
    has_policy = ins_df['policy_number'].notna()
    total_premium = ins_df.loc[has_policy].groupby('policy_number')['premium_amount'].max().sum() if has_policy.any() else ins_df['premium_amount'].sum()
    wellness_count = len(ins_df[ins_df['event_type'] == 'Wellness'])
    wei_score = (wellness_count / len(ins_df)) * 100 if len(ins_df) > 0 else 0

    # --- 2. Household & Name Normalization ---
    name_pattern = r'(?:Dear\s?)(Mr\.|Ms\.)\s?([A-Za-z\s\.]+?)(?=\s(?:on|we|your|would))'
    raw_names = ins_df['raw_body'].apply(
        lambda x: re.search(name_pattern, str(x)).group(2).strip()
        if re.search(name_pattern, str(x)) else None
    ).dropna().tolist()
    final_household = clean_insurance_names(raw_names)
    household_count = len(final_household)

    # --- 3. Quarter Liability Density ---
    ins_df['quarter'] = ins_df[date_col].dt.quarter
    q_burn = ins_df.groupby('quarter')['premium_amount'].sum()
    peak_quarter = f"Q{q_burn.idxmax()}" if not q_burn.empty and not pd.isna(q_burn.idxmax()) else "N/A"

    # --- 4. Premium Concentration Index (PCI) ---
    max_single_premium = ins_df['premium_amount'].max()
    pci_score = (max_single_premium / total_premium * 100) if total_premium > 0 else 0

    # --- 5. Protection Balance Ratio ---
    mix = ins_df['insurance_type'].value_counts()
    health_count = mix.get('Health', 0)
    life_count = mix.get('Life', 0)
    health_vs_life = health_count / life_count if life_count > 0 else (health_count if health_count > 0 else 0)

    # Final Report
    report = {
        "Wellness_Engagement_Index": round(float(wei_score), 2),
        "Total_Premium_Liability": round(float(total_premium), 2),
        "Identified_Household_Size": int(household_count),
        "Avg_Cost_Per_Member": round(float(total_premium) / household_count, 2) if household_count > 0 else 0,
        "Peak_Liability_Quarter": peak_quarter,
        "Premium_Concentration_Index": round(float(pci_score), 2),
        "Health_to_Life_Engagement_Ratio": round(float(health_vs_life), 2)
    }

    return report


def clean_insurance_names(raw_list):
    noise_phrases = [
        r'on behalf of.*', r'thank you for choosing.*', r'niva bupa.*',
        r'we hope this message.*', r'your policy is now active.*', r' Mam$', r' Mamta$'
    ]
    cleaned_names = []
    for text in raw_list:
        if not text: continue
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