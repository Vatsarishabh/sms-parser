import re
import pandas as pd
import numpy as np

def parse_insurance_sms(data: pd.DataFrame):
    df = data.copy()

    def extract_insurance_features(row):
        msg = str(row['body'])

        if pd.isna(msg) or msg.lower() == 'nan':
            return pd.Series([None, None, None, None])

        # 1. Identify Entity
        entity = None
        if "Niva Bupa" in msg: entity = "Niva Bupa (Health)"
        elif "LIC" in msg: entity = "LIC (Life)"


        category, policy_no, amount = None, None, None

        if entity:
          # 2. Identify Event Category
          category = None
          if "renewed" in msg.lower() or "renewal" in msg.lower(): category = "Renewal"
          elif "due" in msg.lower(): category = "Premium Due"
          elif "active" in msg.lower(): category = "New/Active Policy"
          elif "health check-up" in msg.lower(): category = "Service/Wellness"
          elif "Survival Benefit" in msg: category = "Payout/Benefit"

          # 3. Policy Number Extraction
          policy_match = re.search(r'(?:Policy\s?No\.?\s?)(\d+)', msg, re.I)
          policy_no = policy_match.group(1) if policy_match else None

          # 4. Amount Extraction (Handling masked values)
          amt_match = re.search(r'Rs\.?\s?\**(\d+\.\d{2})', msg)
          amount = float(amt_match.group(1)) if amt_match else None

        return pd.Series([entity, category, policy_no, amount])

    df[['insurance_insurer', 'insurance_event_type', 'insurance_policy_no', 'insurance_premium_amt']] = df.apply(extract_insurance_features, axis=1)
    return df

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

def generate_insurance_insights(df):
    ins_df = df[df['insurance_insurer'].notna()].copy()
    if ins_df.empty: return None

    # Ensure date context
    if not pd.api.types.is_datetime64_any_dtype(ins_df['date']):
        ins_df['date'] = pd.to_datetime(ins_df['date'], unit='ms', errors='coerce')

    if ins_df.empty or ins_df['date'].isna().all(): return None

    # --- 1. Basic Metrics ---
    total_premium = ins_df.groupby('insurance_policy_no')['insurance_premium_amt'].max().sum()
    wellness_count = len(ins_df[ins_df['insurance_event_type'] == 'Service/Wellness'])
    wei_score = (wellness_count / len(ins_df)) * 100 if len(ins_df) > 0 else 0

    # --- 2. Household & Name Normalization ---
    name_pattern = r'(?:Dear\s?)(Mr\.|Ms\.)\s?([A-Za-z\s\.]+?)(?=\s(?:on|we|your|would))'
    raw_names = ins_df['body'].apply(lambda x: re.search(name_pattern, str(x)).group(2).strip() if re.search(name_pattern, str(x)) else None).dropna().tolist()
    final_household = clean_insurance_names(raw_names)
    household_count = len(final_household)

    # --- 3. Quarter Liability Density ---
    ins_df['quarter'] = ins_df['date'].dt.quarter
    q_burn = ins_df.groupby('quarter')['insurance_premium_amt'].sum()
    peak_quarter = f"Q{q_burn.idxmax()}" if not q_burn.empty and not pd.isna(q_burn.idxmax()) else "N/A"

    # --- 4. Premium Concentration Index (PCI) ---
    max_single_premium = ins_df['insurance_premium_amt'].max()
    pci_score = (max_single_premium / total_premium * 100) if total_premium > 0 else 0

    # --- 5. Protection Balance Ratio ---
    mix = ins_df['insurance_insurer'].value_counts()
    health_count = mix.get('Niva Bupa (Health)', 0)
    life_count = mix.get('LIC (Life)', 0)
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

    