from collections import defaultdict
from src.utils import parse_timestamp


def _calculate_average_monthly_burn(shop_data):
    """Calculate average monthly burn from a list of shopping dicts."""
    if not shop_data:
        return 0.0

    monthly_totals = defaultdict(float)
    for row in shop_data:
        dt = parse_timestamp(row.get("date"))
        if dt is None:
            continue
        amt = row.get("shopping_amount") or 0
        net = -amt if row.get("shopping_is_refund") else amt
        key = (dt.year, dt.month)
        monthly_totals[key] += net

    if not monthly_totals:
        return 0.0
    return round(sum(monthly_totals.values()) / len(monthly_totals), 2)


def generate_unified_persona(shop_data, shop, ins, inv):
    """Generate cross-domain persona from shopping, insurance, and investment insights.

    Parameters
    ----------
    shop_data : list[dict] | pd.DataFrame
        Shopping rows (dicts with 'date', 'shopping_amount', 'shopping_is_refund').
    shop : dict
        Shopping insight report.
    ins : dict
        Insurance insight report.
    inv : dict
        Investment insight report.
    """
    # Accept both list[dict] and DataFrame for backwards compatibility
    if hasattr(shop_data, "to_dict"):
        shop_data = shop_data.to_dict(orient="records")

    avg_shop_burn = _calculate_average_monthly_burn(shop_data)

    monthly_inv = inv.get("Velocity_Metrics", {}).get("Verified_Monthly_Commitment_L3M", 0)
    if monthly_inv > 0:
        burn_build_ratio = avg_shop_burn / monthly_inv
    elif avg_shop_burn > 0:
        burn_build_ratio = 999.99  # all burn, no build
    else:
        burn_build_ratio = 0.0

    wellness = ins.get("Wellness_Engagement_Index", 0)
    mf_share = inv.get("Portfolio_Health", {}).get("Asset_Wallet_Share", {}).get("Mutual Fund", 0)
    impulse = shop.get("Impulse_Purchase_Index", 0)
    responsibility_score = wellness + mf_share - impulse

    payday_vel = shop.get("Payday_Splurge_Velocity", 0)
    is_clashing = "High" if payday_vel > 0.8 else "Low"

    aci = shop.get("Aggregator_Conflict_Index", {})
    switch_ratio = aci.get("Switch_Consistency_Ratio", 0)
    refund_pct = shop.get("Refund_Rate_Percentage", 0)
    value_hunter_signal = (switch_ratio * 100 + refund_pct) / 2

    return {
        "Unified_Persona": {
            "Segment": "The Disciplined Modernist" if responsibility_score > 100 else "The Impulse-Heavy Professional",
            "Disposable_Income_Health": "Strained" if burn_build_ratio > 10 else "Balanced",
        },
        "Cross_Domain_Metrics": {
            "Burn_to_Build_Multiple": round(float(burn_build_ratio), 2),
            "Future_Proof_Score": round(float(responsibility_score), 2),
            "Value_Hunting_Intensity": f"{value_hunter_signal:.1f}%",
            "Liquidity_Conflict_Risk": is_clashing,
        },
    }
