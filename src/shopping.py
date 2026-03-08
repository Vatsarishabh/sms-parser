import re
import pandas as pd
from src.utils import parse_timestamp

KNOWN_MERCHANTS = {
    "zomato": "Zomato", "swiggy": "Swiggy", "amazon": "Amazon",
    "flipkart": "Flipkart", "myntra": "Myntra", "bigbasket": "BigBasket",
    "blinkit": "Blinkit", "nykaa": "Nykaa", "ajio": "Ajio", "meesho": "Meesho",
    "croma": "Croma",
}

def identify_merchant(text):
    """Identify merchant from SMS body text."""
    if not isinstance(text, str):
        return None
    t = text.lower()
    for key, name in KNOWN_MERCHANTS.items():
        if key in t:
            return name
    return None

def build_shopping_df(parsed_dicts):
    """Build a shopping DataFrame from a list of parsed SMS dicts (any category).

    Scans raw_body for known merchants and extracts shopping features.
    Works with TransactionParsed dicts or any dict with 'raw_body', 'timestamp', 'amount' keys.
    """
    rows = []
    for d in parsed_dicts:
        merchant = identify_merchant(d.get("raw_body", ""))
        if not merchant:
            continue

        body = d.get("raw_body", "").lower()
        is_spend = False
        is_refund = False

        if any(x in body for x in ["spent", "paid", "debited", "spent@"]):
            is_spend = True
        elif any(x in body for x in ["refund", "credited", "initiated"]):
            is_refund = True

        # Filter noise
        if any(x in body for x in ["otp", "standing instructions", "slot booked", "to accept"]):
            is_spend = False
            is_refund = False

        amount = d.get("amount")
        if amount is None and (is_spend or is_refund):
            amt_match = re.search(r'(?:INR|Rs\.?)\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', d.get("raw_body", ""), re.I)
            if amt_match:
                amount = float(amt_match.group(1).replace(',', ''))

        source = None
        raw = d.get("raw_body", "")
        if "Card XX" in raw:
            source = "Credit Card"
        elif "A/C XX" in raw or "UPI" in raw:
            source = "Bank/UPI"

        rows.append({
            "date": d.get("timestamp"),
            "shopping_merchant": merchant,
            "shopping_is_spend": is_spend,
            "shopping_is_refund": is_refund,
            "shopping_amount": amount,
            "shopping_source": source,
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["date","shopping_merchant","shopping_is_spend","shopping_is_refund","shopping_amount","shopping_source"])

def generate_shopping_insights(data):
    """Generate shopping insights from a shopping DataFrame or list of parsed dicts."""
    if isinstance(data, list):
        df = build_shopping_df(data)
    else:
        df = data

    # Ensure date is datetime and filter for shopping only
    shop_df = df[df['shopping_merchant'].notna()].copy()
    if shop_df.empty:
        return None

    shop_df['date'] = shop_df['date'].apply(lambda v: parse_timestamp(v))
    shop_df['date'] = pd.to_datetime(shop_df['date'], errors='coerce')
    shop_df = shop_df.sort_values('date').reset_index(drop=True)

    # 1. Feature Preparation
    shop_df['net_amt'] = shop_df.apply(lambda x: -x['shopping_amount'] if x['shopping_is_refund'] else (x['shopping_amount'] if x['shopping_is_spend'] else 0), axis=1)
    shop_df['hour'] = shop_df['date'].dt.hour
    shop_df['day'] = shop_df['date'].dt.day
    shop_df['is_weekend'] = shop_df['date'].dt.dayofweek.isin([5, 6])
    shop_df['month_year'] = shop_df['date'].dt.to_period('M')

    # Filter for last 3 months only
    periods = shop_df['month_year'].unique()
    last_3_months = periods[-3:]
    monthly_burn = shop_df[shop_df['month_year'].isin(last_3_months)].groupby('month_year')['net_amt'].sum()

    spend_count = shop_df['shopping_is_spend'].sum()
    refund_ratio = (shop_df['shopping_is_refund'].sum() / spend_count * 100) if spend_count > 0 else 0

    top_merchant = shop_df.groupby('shopping_merchant')['net_amt'].sum().idxmax() if not shop_df.empty else "N/A"

    weekday_spend = shop_df[~shop_df['is_weekend']]['net_amt'].sum()
    weekend_ratio = shop_df[shop_df['is_weekend']]['net_amt'].sum() / weekday_spend if weekday_spend > 0 else 0

    avg_ticket_instrument = shop_df.groupby('shopping_source')['net_amt'].mean()
    late_night_orders = len(shop_df[shop_df['hour'].isin([23, 0, 1, 2, 3])])


    # Identify every time the merchant changes from the previous order
    food_apps = shop_df[shop_df['shopping_merchant'].isin(['Swiggy', 'Zomato'])].copy()
    aggregator_conflict = {"Total_Brand_Switches": 0, "Switch_Consistency_Ratio": 0.0}
    if len(food_apps) > 1:
        food_apps['switched'] = food_apps['shopping_merchant'] != food_apps['shopping_merchant'].shift(1)
        total_switches = max(0, food_apps['switched'].sum() - 1)
        switch_ratio = total_switches / len(food_apps)
        aggregator_conflict = {
            "Total_Brand_Switches": int(total_switches),
            "Switch_Consistency_Ratio": round(float(switch_ratio), 2)
        }

    # B. Payday Splurge Velocity
    payday_spend = shop_df[shop_df['day'] <= 10]['net_amt'].mean()
    mid_month_spend = shop_df[shop_df['day'] > 10]['net_amt'].mean()
    payday_velocity = payday_spend / mid_month_spend if mid_month_spend > 0 else 0

    # C. Churn & Impulse
    max_date = shop_df['date'].max()
    last_30d_count = len(shop_df[shop_df['date'] > (max_date - pd.Timedelta(days=30))])
    impulse_score = (len(shop_df[shop_df['net_amt'] < 300]) / len(shop_df)) * 100 if not shop_df.empty else 0

    # Final Report Assembly
    report = {
        "Total_Monthly_Burn_L3M": {str(k):f"Rs {round(v)}" for k,v in monthly_burn.to_dict().items()},
        "Refund_Rate_Percentage": round(float(refund_ratio), 2),
        "Dominant_Merchant": top_merchant,
        "Weekend_Spend_Ratio": round(float(weekend_ratio), 2),
        "Avg_Ticket_Credit_vs_UPI": avg_ticket_instrument.to_dict(),
        "Late_Night_Order_Count": late_night_orders,
        "Aggregator_Conflict_Index": aggregator_conflict,
        "Payday_Splurge_Velocity": round(float(payday_velocity), 2),
        "Impulse_Purchase_Index": round(float(impulse_score), 2),
        "Latest_30d_Velocity": last_30d_count
    }

    return report