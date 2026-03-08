"""
persona.py
----------
Unified cross-domain persona generator. Self-contained (no pandas/numpy).
"""

from collections import defaultdict
from .utils import parse_timestamp, r2


def _calculate_average_monthly_burn(feature_store):
    """Calculate average monthly burn from the feature store by scanning for shopping merchants."""
    if not feature_store:
        return 0.0

    KNOWN_MERCHANTS_LOWER = {
        "zomato", "swiggy", "amazon", "flipkart", "myntra", "bigbasket",
        "blinkit", "nykaa", "ajio", "meesho", "croma",
    }

    monthly_totals = defaultdict(float)
    for d in feature_store:
        raw = d.get("raw_body", "")
        if not isinstance(raw, str):
            continue
        body_lower = raw.lower()
        has_merchant = any(m in body_lower for m in KNOWN_MERCHANTS_LOWER)
        if not has_merchant:
            continue

        dt = parse_timestamp(d.get("timestamp"))
        if dt is None:
            continue

        amt = d.get("amount") or 0
        is_refund = any(x in body_lower for x in ["refund", "credited", "initiated"])
        is_spend = any(x in body_lower for x in ["spent", "paid", "debited", "spent@"])
        # Filter noise
        if any(x in body_lower for x in ["otp", "standing instructions", "slot booked", "to accept"]):
            is_spend = False
            is_refund = False

        if is_refund:
            net = -amt
        elif is_spend:
            net = amt
        else:
            net = 0

        key = (dt.year, dt.month)
        monthly_totals[key] += net

    if not monthly_totals:
        return 0.0
    return round(sum(monthly_totals.values()) / len(monthly_totals), 2)


def generate_persona_insights(
    shopping_insights: dict,
    insurance_insights: dict,
    investment_insights: dict,
    feature_store: list[dict],
) -> dict | None:
    """Generate unified cross-domain persona insights.

    Outputs the final shape (merged fmt_unified).

    Parameters
    ----------
    shopping_insights : dict
        Shopping insight report (final shape from shopping generator).
    insurance_insights : dict
        Insurance insight report (final shape from insurance generator).
    investment_insights : dict
        Investment insight report (final shape from investment generator).
    feature_store : list[dict]
        Full feature store (used to compute average monthly shopping burn).
    """
    if not shopping_insights or not insurance_insights or not investment_insights:
        return None

    avg_shop_burn = _calculate_average_monthly_burn(feature_store)

    # Investment insights are already in final shape
    monthly_inv = investment_insights.get("velocity", {}).get("monthly_commitment_l3m", 0)
    if monthly_inv > 0:
        burn_build_ratio = avg_shop_burn / monthly_inv
    elif avg_shop_burn > 0:
        burn_build_ratio = 999.99
    else:
        burn_build_ratio = 0.0

    # Insurance insights are already in final shape
    wellness = insurance_insights.get("engagement", {}).get("wellness_index_pct", 0)

    # Investment wallet share: get mutual_fund_pct
    mf_share = investment_insights.get("portfolio", {}).get("wallet_share", {}).get("mutual_fund_pct", 0)

    # Shopping insights are already in final shape
    impulse = shopping_insights.get("behavior", {}).get("impulse_purchase_index_pct", 0)
    responsibility_score = (wellness or 0) + (mf_share or 0) - (impulse or 0)

    payday_vel = shopping_insights.get("behavior", {}).get("payday_splurge_velocity", 0)
    is_clashing = "High" if (payday_vel or 0) > 0.8 else "Low"

    switch_ratio = shopping_insights.get("merchants", {}).get("merchants_switch_ratio", 0)
    refund_pct = shopping_insights.get("behavior", {}).get("refund_rate_pct", 0)
    value_hunter_signal = ((switch_ratio or 0) * 100 + (refund_pct or 0)) / 2

    return {
        "segment": "The Disciplined Modernist" if responsibility_score > 100 else "The Impulse-Heavy Professional",
        "disposable_income_health": "Strained" if burn_build_ratio > 10 else "Balanced",
        "scores": {
            "future_proof_score": r2(float(responsibility_score)),
            "burn_to_build_multiple": r2(float(burn_build_ratio)),
            "value_hunting_intensity_pct": r2(float(value_hunter_signal)),
            "liquidity_conflict_risk": is_clashing,
        },
    }
