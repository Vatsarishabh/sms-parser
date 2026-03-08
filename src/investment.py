import re
import pandas as pd
import numpy as np
from src.models import InvestmentParsed
from src.utils import parse_timestamp


def parse_investment_model(body, address, base_fields=None):
    """Parse an investment SMS into an InvestmentParsed dataclass instance.

    Parameters
    ----------
    body : str
        The SMS body text.
    address : str
        The sender address / phone number.
    base_fields : dict, optional
        Pre-computed SMSBase fields to seed the dataclass with.

    Returns
    -------
    InvestmentParsed
    """
    msg = str(body) if body is not None else ""
    msg_upper = msg.upper()
    msg_lower = msg.lower()

    # --- asset_type ---
    asset_type = None
    if any(kw in msg_upper for kw in ("PAMP", "GOLD")):
        asset_type = "Gold"
    elif any(kw in msg_upper for kw in ("FUND", "MOMF", "IPRUMF", "MF", "ICCL", "COIN")):
        asset_type = "Mutual Fund"
    elif any(kw in msg_upper for kw in ("STOCK", "EQUITY", "ZERODHA")):
        asset_type = "Stock"

    # --- platform ---
    platform = None
    for name in ("Groww", "Zerodha", "CAMS", "Coin"):
        if name.upper() in msg_upper:
            platform = name
            break

    # --- event_type ---
    event_type = None
    if "requested money" in msg_lower:
        event_type = "SIP Debit"
    elif re.search(r"allotted|subscription", msg_lower):
        event_type = "Units Allotted"
    elif "registration" in msg_lower:
        event_type = "Registration"
    elif re.search(r"redeem|redeemed", msg_lower):
        event_type = "Redemption"
    elif "dividend" in msg_lower:
        event_type = "Dividend"

    # --- amount ---
    amount = None
    amt_match = re.search(r"Rs\.?\s?(\d+\.?\d*)", msg)
    if amt_match:
        amount = float(amt_match.group(1))

    # --- nav ---
    nav = None
    nav_match = re.search(r"NAV\s?:?\s?(\d+\.?\d*)", msg, re.I)
    if nav_match:
        nav = float(nav_match.group(1))

    # --- units ---
    units = None
    units_match = re.search(r"(\d+\.?\d*)\s*units", msg, re.I)
    if units_match:
        units = float(units_match.group(1))

    # --- flags ---
    is_sip = "sip" in msg_lower
    is_redemption = "redeem" in msg_lower

    # --- fund_name ---
    fund_name = None
    # Try extracting a scheme/fund name from common patterns
    fund_match = re.search(r"(?:scheme|fund)\s*[-:]\s*(.+?)(?:\.|,|$)", msg, re.I)
    if fund_match:
        fund_name = fund_match.group(1).strip()

    # Build keyword arguments, seeding from base_fields if provided
    kwargs = dict(base_fields) if base_fields else {}
    kwargs.update(
        raw_body=msg,
        sender_address=str(address) if address is not None else "",
        sms_category="Investments",
        asset_type=asset_type,
        fund_name=fund_name,
        platform=platform,
        event_type=event_type,
        amount=amount,
        nav=nav,
        units=units,
        is_sip=is_sip,
        is_redemption=is_redemption,
    )

    return InvestmentParsed(**kwargs)


def generate_investment_insights(parsed_dicts, date_col='timestamp'):
    """Generate investment insights from a list of InvestmentParsed dicts.

    Parameters
    ----------
    parsed_dicts : list[dict]
        List of dicts produced by ``InvestmentParsed.to_dict()``.
    date_col : str, optional
        Name of the timestamp column (default ``'timestamp'``).

    Returns
    -------
    dict or None
        Consolidated investment insight report, or None when no valid
        investment rows exist.
    """
    if not parsed_dicts:
        return None

    df = pd.DataFrame(parsed_dicts)

    # Filter rows where asset_type is present (amount can be None for registrations, SIP setups, etc.)
    inv_df = df[df['asset_type'].notna()].copy()
    if inv_df.empty:
        return None

    # Fill missing amounts with 0 for aggregation
    inv_df['amount'] = inv_df['amount'].fillna(0)

    # Ensure timestamp is datetime — handles epoch ms/ns/s and string formats
    if not pd.api.types.is_datetime64_any_dtype(inv_df[date_col]):
        inv_df[date_col] = inv_df[date_col].apply(lambda v: parse_timestamp(v))
        inv_df[date_col] = pd.to_datetime(inv_df[date_col], errors='coerce')
        inv_df = inv_df.dropna(subset=[date_col])
        if inv_df.empty:
            return None

    inv_df = inv_df.sort_values(date_col).reset_index(drop=True)

    if inv_df.empty:
        return None

    # --- 1. Basic & Velocity Features ---
    # Monthly Commitment Velocity (L3M)
    periods = inv_df[date_col].dt.to_period('M').unique()
    last_3_months = periods[-3:] if len(periods) >= 3 else periods
    l3m_df = inv_df[inv_df[date_col].dt.to_period('M').isin(last_3_months)]
    if not l3m_df.empty:
        resampled = l3m_df.resample('ME', on=date_col)['amount'].sum()
        mcv_l3m = resampled.mean() if not resampled.empty else l3m_df['amount'].sum()
    else:
        mcv_l3m = inv_df['amount'].sum()

    # Portfolio Composition
    asset_mix = inv_df.groupby('asset_type')['amount'].agg(['sum', 'count'])
    total_inv_sum = asset_mix['sum'].sum()
    asset_mix['wallet_share_%'] = (asset_mix['sum'] / total_inv_sum * 100) if total_inv_sum > 0 else 0

    # --- 2. Mandate & Reliability Analysis ---
    requests = inv_df[inv_df['raw_body'].str.contains('requested|registration', case=False, na=False)]
    success = inv_df[inv_df['raw_body'].str.contains('subscription|allotted', case=False, na=False)]
    realization_rate = (len(success) / len(requests) * 100) if len(requests) > 0 else 100

    if not requests.empty:
        common_sip_day = requests[date_col].dt.day.mode()[0]
    else:
        common_sip_day = "Unknown"

    # --- 3. Habit & Recency Signals ---
    # Use the latest timestamp in the full dataframe as the snapshot date
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        snapshot_series = df[date_col].apply(lambda v: parse_timestamp(v))
        snapshot_series = pd.to_datetime(snapshot_series, errors='coerce')
        current_snapshot_date = snapshot_series.max()
    else:
        current_snapshot_date = df[date_col].max()

    if not isinstance(current_snapshot_date, pd.Timestamp):
        if isinstance(current_snapshot_date, (int, float, np.integer)):
            current_snapshot_date = pd.to_datetime(current_snapshot_date, unit='ms')
        else:
            current_snapshot_date = pd.to_datetime(current_snapshot_date)

    last_active_date = inv_df[date_col].max()
    if not isinstance(last_active_date, pd.Timestamp):
        last_active_date = pd.to_datetime(last_active_date)

    recency_days = (
        (current_snapshot_date - last_active_date).days
        if not pd.isna(current_snapshot_date) and not pd.isna(last_active_date)
        else 0
    )

    # Tenure/Habit: Total span of investment history
    habit_tenure_days = (
        (last_active_date - inv_df[date_col].min()).days
        if not pd.isna(last_active_date) and not pd.isna(inv_df[date_col].min())
        else 0
    )

    # Consistency: Average gap between any two investment activities
    inv_df['gap'] = inv_df[date_col].diff().dt.days
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
            "Avg_Transaction_Size": round(float(inv_df['amount'].mean()), 2) if not inv_df.empty else 0
        },
        "Reliability_Signals": {
            "Mandate_Realization_Rate": f"{realization_rate:.1f}%",
            "Predicted_SIP_Date": f"Day {common_sip_day} of month",
            "Mandate_Frequency_Count": len(requests),
            "Total_Engagement_Points": len(inv_df)
        }
    }

    return report