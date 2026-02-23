import re
import pandas as pd
import numpy as np

def parse_investment_sms(data: pd.DataFrame):
    df = data.copy()

    def categorize(row):
        msg = str(row['body'])

        if pd.isna(msg) or msg.lower() == 'nan':
            return pd.Series([False, None, None])

        # 1. Broadened Detection: Includes 'requested money' & 'registration'
        inflow_keywords = r'(received|subscription|allotted|requested money|registration for ICCL)'
        is_investment = bool(re.search(inflow_keywords, msg, re.I))

        # Strict Exclusion: Filter out weekly balance reporting
        if re.search(r'(fund bal|securities bal|balance is)', msg, re.I):
            is_investment = False

        # 2. Refined Asset Type Detection
        inv_type = None
        if is_investment:
            msg_upper = msg.upper()
            if any(x in msg_upper for x in ["PAMP", "GOLD"]):
                inv_type = "Gold"
            # Added ICCL, ZERODHA, and COIN to the Mutual Fund category
            elif any(x in msg_upper for x in ["FUND", "MOMF", "IPRUMF", "MF", "ICCL", "COIN"]):
                inv_type = "Mutual Fund"

        # Cleanup: If we can't identify the asset type, we don't flag as investment
        if inv_type is None:
            is_investment = False

        # 3. Amount Extraction
        amount = None
        if is_investment:
            amt_match = re.search(r"Rs\.?\s?(\d+\.?\d*)", msg)
            amount = float(amt_match.group(1)) if amt_match else None

        return pd.Series([is_investment, inv_type, amount])

    df[['is_investment', 'investment_type', 'investment_amount']] = df.apply(categorize, axis=1)
    return df

def generate_investment_insights(df):
    # Filter for active investment rows and ensure temporal context
    inv_df = df[df['is_investment'] == True].copy()
    if inv_df.empty:
        return None

    # Ensure date is datetime
    if not pd.api.types.is_datetime64_any_dtype(inv_df['date']):
        inv_df['date'] = pd.to_datetime(inv_df['date'], unit='ms', errors='coerce')
    
    inv_df = inv_df.sort_values('date').reset_index(drop=True)

    if inv_df.empty:
        return None

    # --- 1. Basic & Velocity Features ---
    # Monthly Commitment Velocity (L3M)
    periods = inv_df['date'].dt.to_period('M').unique()
    last_3_months = periods[-3:] if len(periods) >=3 else periods
    mcv_l3m = inv_df[inv_df['date'].dt.to_period('M').isin(last_3_months)].resample('ME', on='date')['investment_amount'].sum().mean()

    # Portfolio Composition
    asset_mix = inv_df.groupby('investment_type')['investment_amount'].agg(['sum', 'count'])
    total_inv_sum = asset_mix['sum'].sum()
    asset_mix['wallet_share_%'] = (asset_mix['sum'] / total_inv_sum * 100) if total_inv_sum > 0 else 0

    # --- 2. Mandate & Reliability Analysis ---
    requests = inv_df[inv_df['body'].str.contains('requested|registration', case=False, na=False)]
    success = inv_df[inv_df['body'].str.contains('subscription|allotted', case=False, na=False)]
    realization_rate = (len(success) / len(requests) * 100) if len(requests) > 0 else 100

    if not requests.empty:
        common_sip_day = requests['date'].dt.day.mode()[0]
    else:
        common_sip_day = "Unknown"

    # --- 3. Habit & Recency Signals ---
    # Ensure current_snapshot_date is a Timestamp
    current_snapshot_date = df['date'].max()
    if not isinstance(current_snapshot_date, pd.Timestamp):
        if isinstance(current_snapshot_date, (int, float, np.integer)):
            current_snapshot_date = pd.to_datetime(current_snapshot_date, unit='ms')
        else:
            current_snapshot_date = pd.to_datetime(current_snapshot_date)
    
    last_active_date = inv_df['date'].max()
    if not isinstance(last_active_date, pd.Timestamp):
        last_active_date = pd.to_datetime(last_active_date)
        
    recency_days = (current_snapshot_date - last_active_date).days if not pd.isna(current_snapshot_date) and not pd.isna(last_active_date) else 0

    # Tenure/Habit: Total span of investment history
    habit_tenure_days = (last_active_date - inv_df['date'].min()).days if not pd.isna(last_active_date) and not pd.isna(inv_df['date'].min()) else 0

    # Consistency: Average gap between any two investment activities
    inv_df['gap'] = inv_df['date'].diff().dt.days
    avg_gap = inv_df['gap'].mean()

    # --- Final Consolidated Report ---
    report = {
        "Portfolio_Health": {
            "Total_Invested_Value": round(float(total_inv_sum), 2),
            "Dominant_Asset": asset_mix['sum'].idxmax() if not asset_mix.empty else "N/A",
            "Asset_Wallet_Share": asset_mix['wallet_share_%'].to_dict() if isinstance(asset_mix['wallet_share_%'], pd.Series) else {}
        },
        "Recency_Signal": {
            "Days_Since_Last_Action": int(recency_days),
            "Status": "Active" if recency_days < 30 else "Dormant",
            "Last_Activity_Date": last_active_date.strftime('%Y-%m-%d') if not pd.isna(last_active_date) else "N/A"
        },
        "Habit_Signal": {
            "Total_Investment_Tenure": f"{habit_tenure_days} days",
            "Average_Gap_Between_Actions": f"{avg_gap:.1f} days" if not pd.isna(avg_gap) else "N/A",
            "Stability_Score": "High" if habit_tenure_days > 365 else "Developing"
        },
        "Velocity_Metrics": {
            "Verified_Monthly_Commitment_L3M": round(float(mcv_l3m), 2) if not pd.isna(mcv_l3m) else 0,
            "Avg_Transaction_Size": round(float(inv_df['investment_amount'].mean()), 2) if not inv_df.empty else 0
        },
        "Reliability_Signals": {
            "Mandate_Realization_Rate": f"{realization_rate:.1f}%",
            "Predicted_SIP_Date": f"Day {common_sip_day} of month",
            "Mandate_Frequency_Count": len(requests),
            "Total_Engagement_Points": len(inv_df)
        }
    }

    return report
