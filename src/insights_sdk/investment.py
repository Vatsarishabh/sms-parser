"""
investment.py
-------------
Investment insights generator. Self-contained.
"""

import re

import numpy as np
import pandas as pd

from .utils import parse_timestamp, r2


def generate_investment_insights(feature_store: list[dict]) -> dict | None:
    """Generate investment insights from the feature store.

    Filters for sms_category == 'investments', runs the full investment
    analysis pipeline, and outputs the final shape.
    """
    parsed_dicts = [d for d in feature_store if d.get("sms_category") == "investments"]
    if not parsed_dicts:
        return None

    date_col = "timestamp"
    df = pd.DataFrame(parsed_dicts)

    # Ensure expected columns exist (null-stripped dicts may omit them)
    for col in ("asset_type", "amount", "raw_body", "platform", "event_type",
                "is_sip", date_col):
        if col not in df.columns:
            df[col] = None

    # Filter rows where asset_type is present
    inv_df = df[df["asset_type"].notna()].copy()
    if inv_df.empty:
        return None

    inv_df["amount"] = inv_df["amount"].fillna(0)
    inv_df["platform"] = inv_df["platform"].fillna("unknown")

    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(inv_df[date_col]):
        inv_df[date_col] = inv_df[date_col].apply(lambda v: parse_timestamp(v))
        inv_df[date_col] = pd.to_datetime(inv_df[date_col], errors="coerce")
        inv_df = inv_df.dropna(subset=[date_col])
        if inv_df.empty:
            return None

    inv_df = inv_df.sort_values(date_col).reset_index(drop=True)
    if inv_df.empty:
        return None

    # ── 1. Portfolio Composition ──
    asset_mix = inv_df.groupby("asset_type")["amount"].agg(["sum", "count"])
    total_inv_sum = asset_mix["sum"].sum()
    asset_mix["wallet_share_%"] = (asset_mix["sum"] / total_inv_sum * 100) if total_inv_sum > 0 else 0

    raw_share = asset_mix["wallet_share_%"].to_dict() if isinstance(asset_mix["wallet_share_%"], pd.Series) else {}
    wallet_share = {
        k.lower().replace(" ", "_") + "_pct": r2(v)
        for k, v in raw_share.items()
    }

    # ── 2. Velocity ──
    periods = inv_df[date_col].dt.to_period("M").unique()
    last_3_months = periods[-3:] if len(periods) >= 3 else periods
    l3m_df = inv_df[inv_df[date_col].dt.to_period("M").isin(last_3_months)]
    if not l3m_df.empty:
        resampled = l3m_df.resample("ME", on=date_col)["amount"].sum()
        mcv_l3m = resampled.mean() if not resampled.empty else l3m_df["amount"].sum()
    else:
        mcv_l3m = inv_df["amount"].sum()

    # ── 3. Mandate & Reliability ──
    requests = inv_df[inv_df["raw_body"].str.contains("requested|registration", case=False, na=False)]
    success = inv_df[inv_df["raw_body"].str.contains("subscription|allotted", case=False, na=False)]
    realization_rate = (len(success) / len(requests) * 100) if len(requests) > 0 else 100

    if not requests.empty:
        common_sip_day = requests[date_col].dt.day.mode()[0]
    else:
        common_sip_day = "Unknown"

    try:
        predicted_sip_day = int(common_sip_day)
    except Exception:
        predicted_sip_day = None

    # ── 4. Activity & Recency ──
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        snapshot_series = df[date_col].apply(lambda v: parse_timestamp(v))
        snapshot_series = pd.to_datetime(snapshot_series, errors="coerce")
        current_snapshot_date = snapshot_series.max()
    else:
        current_snapshot_date = df[date_col].max()

    if not isinstance(current_snapshot_date, pd.Timestamp):
        if isinstance(current_snapshot_date, (int, float, np.integer)):
            current_snapshot_date = pd.to_datetime(current_snapshot_date, unit="ms")
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

    habit_tenure_days = (
        (last_active_date - inv_df[date_col].min()).days
        if not pd.isna(last_active_date) and not pd.isna(inv_df[date_col].min())
        else 0
    )

    inv_df["gap"] = inv_df[date_col].diff().dt.days
    avg_gap = inv_df["gap"].mean()

    tenure_days = int(habit_tenure_days) if habit_tenure_days else None
    avg_gap_days = float(avg_gap) if not pd.isna(avg_gap) else None

    # ── 5. Platform Breakdown ──
    platforms_section = _build_platform_breakdown(inv_df)

    # ── 6. SIP Behavior ──
    sip_section = _build_sip_behavior(inv_df, date_col)

    # ── 7. Investor Profile ──
    profile_section = _build_investor_profile(inv_df, platforms_section)

    # ── Final output ──
    return {
        "portfolio": {
            "total_invested": r2(float(total_inv_sum) if not pd.isna(total_inv_sum) else 0),
            "dominant_asset": asset_mix["sum"].idxmax() if not asset_mix.empty else None,
            "wallet_share": wallet_share,
        },
        "activity": {
            "last_action_date": last_active_date.strftime("%Y-%m-%d") if not pd.isna(last_active_date) else None,
            "days_since_last_action": int(recency_days),
            "status": "Active" if recency_days < 30 else "Dormant",
            "tenure_days": tenure_days,
            "avg_gap_between_actions_days": avg_gap_days,
            "stability_score": "High" if habit_tenure_days > 365 else "Developing",
        },
        "velocity": {
            "monthly_commitment_l3m": r2(float(mcv_l3m) if not pd.isna(mcv_l3m) else 0),
            "avg_transaction_size": r2(float(inv_df["amount"].mean()) if not inv_df.empty else 0),
        },
        "reliability": {
            "mandate_realization_rate": f"{realization_rate:.1f}%",
            "predicted_sip_day": predicted_sip_day,
            "mandate_count": len(requests),
            "total_engagement_points": len(inv_df),
        },
        "platforms": platforms_section,
        "sip_behavior": sip_section,
        "investor_profile": profile_section,
    }


# ── Helper: Platform Breakdown ──

def _build_platform_breakdown(inv_df: pd.DataFrame) -> dict:
    """Group investment activity by platform."""
    plat_groups = inv_df.groupby("platform")

    breakdown = {}
    for plat_name, grp in plat_groups:
        asset_types = sorted(grp["asset_type"].dropna().unique().tolist())
        # snake_case the asset types for consistency
        asset_types = [a.lower().replace(" ", "_") for a in asset_types]
        breakdown[plat_name.lower().replace(" ", "_")] = {
            "asset_types": asset_types,
            "txn_count": len(grp),
            "total_invested": r2(float(grp["amount"].sum())),
        }

    platform_count = len(breakdown)
    if platform_count >= 3:
        diversification = "high"
    elif platform_count == 2:
        diversification = "moderate"
    else:
        diversification = "low"

    return {
        "count": platform_count,
        "breakdown": breakdown,
        "diversification": diversification,
    }


# ── Helper: SIP Behavior ──

def _build_sip_behavior(inv_df: pd.DataFrame, date_col: str) -> dict:
    """Detect SIP and recurring investment patterns."""
    # Detect SIP-like rows: explicit is_sip flag, or recurring patterns
    sip_mask = inv_df["is_sip"].fillna(False).astype(bool)
    # Also treat "SIP Debit", "Purchase" with small recurring amounts as SIP-like
    event_sip_mask = inv_df["event_type"].isin(["sip_debit", "purchase", "units_allotted"])
    combined_mask = sip_mask | event_sip_mask

    sip_df = inv_df[combined_mask]

    # Micro-DCA detection: small recurring amounts (same amount, high frequency)
    micro_dca = False
    micro_dca_detail = None
    if not sip_df.empty:
        amt_counts = sip_df.groupby(["platform", "amount"]).size()
        for (plat, amt), count in amt_counts.items():
            if count >= 5 and amt <= 100:
                micro_dca = True
                micro_dca_detail = {
                    "platform": plat.lower().replace(" ", "_"),
                    "amount": r2(float(amt)),
                    "occurrences": int(count),
                }
                break

    # SIP frequency per platform
    sip_platforms = []
    if not sip_df.empty:
        for plat, grp in sip_df.groupby("platform"):
            if len(grp) < 2:
                continue
            gaps = grp[date_col].diff().dt.days.dropna()
            avg_freq = float(gaps.mean()) if not gaps.empty else None
            sip_platforms.append({
                "platform": plat.lower().replace(" ", "_"),
                "txn_count": len(grp),
                "avg_frequency_days": r2(avg_freq) if avg_freq else None,
            })

    return {
        "active_sips_detected": len(sip_platforms),
        "micro_dca_detected": micro_dca,
        "micro_dca_detail": micro_dca_detail,
        "sip_platforms": sip_platforms,
    }


# ── Helper: Investor Profile ──

def _build_investor_profile(inv_df: pd.DataFrame, platforms: dict) -> dict:
    """Derive investor style from behavior signals."""
    platform_count = platforms.get("count", 0)
    asset_types = inv_df["asset_type"].dropna().unique()

    # Style classification
    has_direct_plan = inv_df["raw_body"].str.contains("direct plan", case=False, na=False).any()
    has_revision = inv_df["event_type"].isin(["scheme_revision"]).any() if "event_type" in inv_df.columns else False

    if platform_count >= 3 or (has_direct_plan and platform_count >= 2):
        style = "self_directed"
    elif platform_count >= 2:
        style = "diversified"
    else:
        style = "single_platform"

    return {
        "style": style,
        "active_management_signals": int(has_revision),
        "asset_type_count": len(asset_types),
        "uses_direct_plans": has_direct_plan,
    }
