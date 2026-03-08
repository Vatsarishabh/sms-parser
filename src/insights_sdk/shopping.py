"""
shopping.py
-----------
Shopping insights generator. Self-contained.
Scans ALL parsed SMS for merchant mentions in raw_body.
"""

import re

import pandas as pd

from .utils import parse_timestamp, r2


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
    """Build a shopping DataFrame from a list of parsed SMS dicts (any category)."""
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
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["date", "shopping_merchant", "shopping_is_spend", "shopping_is_refund", "shopping_amount", "shopping_source"]
    )


def generate_shopping_insights(feature_store: list[dict]) -> dict | None:
    """Generate shopping insights from the feature store.

    NOTE: Shopping scans ALL parsed SMS for merchant mentions in raw_body.
    Outputs the final shape (merged fmt_shopping).
    """
    df = build_shopping_df(feature_store)

    shop_df = df[df["shopping_merchant"].notna()].copy()
    if shop_df.empty:
        return None

    shop_df["date"] = shop_df["date"].apply(lambda v: parse_timestamp(v))
    shop_df["date"] = pd.to_datetime(shop_df["date"], errors="coerce")
    shop_df = shop_df.sort_values("date").reset_index(drop=True)

    # Feature Preparation
    shop_df["net_amt"] = shop_df.apply(
        lambda x: -x["shopping_amount"] if x["shopping_is_refund"]
        else (x["shopping_amount"] if x["shopping_is_spend"] else 0),
        axis=1,
    )
    shop_df["hour"] = shop_df["date"].dt.hour
    shop_df["day"] = shop_df["date"].dt.day
    shop_df["is_weekend"] = shop_df["date"].dt.dayofweek.isin([5, 6])
    shop_df["month_year"] = shop_df["date"].dt.to_period("M")

    # Last 3 months
    periods = shop_df["month_year"].unique()
    last_3_months = periods[-3:]
    monthly_burn_raw = shop_df[shop_df["month_year"].isin(last_3_months)].groupby("month_year")["net_amt"].sum()

    spend_count = shop_df["shopping_is_spend"].sum()
    refund_ratio = (shop_df["shopping_is_refund"].sum() / spend_count * 100) if spend_count > 0 else 0

    top_merchant = shop_df.groupby("shopping_merchant")["net_amt"].sum().idxmax() if not shop_df.empty else "N/A"

    weekday_spend = shop_df[~shop_df["is_weekend"]]["net_amt"].sum()
    weekend_ratio = shop_df[shop_df["is_weekend"]]["net_amt"].sum() / weekday_spend if weekday_spend > 0 else 0

    avg_ticket_instrument = shop_df.groupby("shopping_source")["net_amt"].mean()
    late_night_orders = len(shop_df[shop_df["hour"].isin([23, 0, 1, 2, 3])])

    # Aggregator conflict
    food_apps = shop_df[shop_df["shopping_merchant"].isin(["Swiggy", "Zomato"])].copy()
    total_switches = 0
    switch_ratio = 0.0
    if len(food_apps) > 1:
        food_apps["switched"] = food_apps["shopping_merchant"] != food_apps["shopping_merchant"].shift(1)
        total_switches = max(0, food_apps["switched"].sum() - 1)
        switch_ratio = round(float(total_switches / len(food_apps)), 2)

    # Payday Splurge Velocity
    payday_spend = shop_df[shop_df["day"] <= 10]["net_amt"].mean()
    mid_month_spend = shop_df[shop_df["day"] > 10]["net_amt"].mean()
    payday_velocity = payday_spend / mid_month_spend if mid_month_spend > 0 else 0

    # Churn & Impulse
    max_date = shop_df["date"].max()
    last_30d_count = len(shop_df[shop_df["date"] > (max_date - pd.Timedelta(days=30))])
    impulse_score = (len(shop_df[shop_df["net_amt"] < 300]) / len(shop_df)) * 100 if not shop_df.empty else 0

    # --- Format monthly burn into final shape ---
    monthly_burn = {}
    for k, v in monthly_burn_raw.to_dict().items():
        try:
            monthly_burn[str(k)] = int(round(v))
        except Exception:
            monthly_burn[str(k)] = v

    # --- Avg ticket by instrument ---
    raw_ticket = avg_ticket_instrument.to_dict()
    avg_ticket = {
        "bank_upi": r2(raw_ticket.get("Bank/UPI")),
        "credit_card": r2(raw_ticket.get("Credit Card")),
    }

    # --- Final output in the target shape ---
    return {
        "monthly_burn_l3m": monthly_burn,
        "merchants": {
            "dominant": top_merchant,
            "merchants_switch_count": int(total_switches),
            "merchants_switch_ratio": r2(float(switch_ratio)),
        },
        "behavior": {
            "refund_rate_pct": r2(float(refund_ratio)),
            "weekend_spend_ratio": r2(float(weekend_ratio)),
            "late_night_orders": int(late_night_orders),
            "payday_splurge_velocity": r2(float(payday_velocity)),
            "impulse_purchase_index_pct": r2(float(impulse_score)),
            "last_30d_order_count": int(last_30d_count),
        },
        "avg_ticket_by_instrument": avg_ticket,
    }
