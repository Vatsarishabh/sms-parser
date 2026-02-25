import os
import sys
import math
import pandas as pd
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

parser_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(parser_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.promotion_analysis import analyze_promotions
from src.tagger import process_sms_df
from src.transaction import analyze_transactions
from src.transaction_summary import monthly_and_overall_insights
from src.investment import parse_investment_sms, generate_investment_insights
from src.insurance import parse_insurance_sms, generate_insurance_insights
from src.shopping_spend import parse_shopping_sms, generate_shopping_insights
from src.in_in_sh import generate_unified_persona
from src.loan import generate_loan_insights

app = FastAPI(title="SMS Financial Parser API")


class SMSRequest(BaseModel):
    sms_data: List[Dict[str, Any]]

# UTILS
def sanitize(obj):
    """Recursively convert NaN / Inf / Timestamps / numpy scalars to JSON-safe types."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(i) for i in obj]
    elif isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else round(obj, 4)
    elif hasattr(obj, 'isoformat'):
        return str(obj)
    elif hasattr(obj, 'item'):          # numpy scalar
        return obj.item()
    return obj


def r2(val, fallback=None):
    """Round to 2 dp; return fallback if None/NaN."""
    try:
        if val is None or math.isnan(float(val)):
            return fallback
        return round(float(val), 2)
    except Exception:
        return fallback


# META
def build_meta(df_raw, df_promo, df_rest, df_tagged,
               invest_insights, insur_insights, shop_insights, unified_insights):

    processed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    date_range = {"from": None, "to": None}
    if "date" in df_raw.columns:
        dates = pd.to_datetime(df_raw["date"], unit="ms", errors="coerce").dropna()
        if not dates.empty:
            date_range = {
                "from": dates.min().strftime("%Y-%m-%d"),
                "to":   dates.max().strftime("%Y-%m-%d"),
            }

    domain_status = {
        "banking":        True,
        "investment":     invest_insights  is not None,
        "insurance":      insur_insights   is not None,
        "shopping":       shop_insights    is not None,
        "unified_persona": unified_insights is not None,
    }

    # Count categories from df_tagged
    category_counts = {}
    if df_tagged is not None and "sms_category" in df_tagged.columns:
        counts = df_tagged["sms_category"].value_counts().to_dict()
        category_counts = {str(k).lower().replace(" ", "_"): int(v) for k, v in counts.items()}
    else:
        category_counts = {"transactional_processed": len(df_rest)}

    return {
        "processed_at": processed_at,
        "date_range":   date_range,
        "sms_counts": {
            "total_received":       len(df_raw),
            "promotional_filtered": len(df_promo),
            **category_counts
        },
        "unique_senders":   int(df_raw["address"].nunique()) if "address" in df_raw.columns else 0,
        "domains_analyzed": [d for d, ok in domain_status.items() if ok],
        "domains_skipped":  [d for d, ok in domain_status.items() if not ok],
    }


# SECTION FORMATTERS
def fmt_promotional(promo: dict):
    return {
        "total_messages": promo.get("total_promotional_messages", 0),
        "breakdown": {
            "credit_card":       promo.get("credit_card_messages", 0),
            "offer_or_discount": promo.get("offer_or_discount_messages", 0),
            "lending_app":       promo.get("lending_app_messages", 0),
            "other":             promo.get("other_messages", 0),
        },
        "avg_limit_offers": {
            "credit_card_last5": r2(promo.get("avg_last5_cc_limit", 0)),
            "lending_app_last5": r2(promo.get("avg_last5_lending_limit", 0)),
        },
    }


def fmt_banking(b: dict):
    if not b:
        return None

    def window(data, rows):
        return {
            "rows_analyzed": rows,
            "spend": {
                "total":       r2(data.get("spend_total", 0)),
                "txn_count":   int(data.get("spend_txn_count", 0)),
                "avg_per_txn": r2(data.get("avg_spend_per_txn")),
            },
            "earn": {
                "total":       r2(data.get("earn_total", 0)),
                "txn_count":   int(data.get("earn_txn_count", 0)),
                "avg_per_txn": r2(data.get("avg_earn_per_txn")),
            },
            "top_channel": data.get("top_channel"),
        }

    def channel(data):
        return {
            "upi": {
                "spend_total": r2(data.get("upi_spend_total", 0)),
                "txn_count":   int(data.get("upi_spend_txn_count", 0)),
                "avg_ticket":  r2(data.get("upi_ticket_size")),
            },
            "credit_card": {
                "spend_total": r2(data.get("cc_spend_total", 0)),
                "txn_count":   int(data.get("cc_spend_txn_count", 0)),
                "avg_ticket":  r2(data.get("cc_ticket_size")),
            },
        }

    overall    = b.get("overall", {})
    last_month = b.get("last_month", {})

    bank_details = b.get("bank_account_details", [])
    raw_card_details = b.get("credit_card_details", [])

    # Filter credit cards to prioritize those with actual limits/bills
    cards_with_values = []
    cards_empty = []
    for c in raw_card_details:
        v_bal   = c.get("balance", {}).get("value")
        v_bill  = c.get("last_bill", {}).get("value")
        v_limit = c.get("credit_limit", {}).get("value")
        if v_bal is not None or v_bill is not None or v_limit is not None:
            cards_with_values.append(c)
        else:
            cards_empty.append(c)

    est_total_cc = int(overall.get("num_credit_cards", 0))
    # Final count is either the number of valid cards we found, or the estimate (whichever is larger)
    target_count = max(len(cards_with_values), est_total_cc)

    final_cards = cards_with_values[:]
    # If we haven't reached target_count, pad with the empty ones (just up to the count)
    if len(final_cards) < target_count:
        needed = target_count - len(final_cards)
        final_cards.extend(cards_empty[:needed])

    # If the padding brought us over, or we simply have the exact number, 
    # the 'total' is always exactly the length of the final array shown.
    final_card_count = len(final_cards)

    return {
        "accounts": {
            "bank_accounts": {
                "total":   int(overall.get("num_bank_accounts", 0)),
                "details": bank_details,
            },
            "credit_cards": {
                "total":   final_card_count,
                "details": final_cards,
            },
        },
        "cash_flow": {
            "overall":    window(overall,    b.get("overall_rows", 0)),
            "last_month": window(last_month, b.get("last_month_rows", 0)),
        },
        "channel_breakdown": {
            "overall":    channel(overall),
            "last_month": channel(last_month),
        },
    }


def fmt_investment(inv: dict):
    if not inv:
        return None

    ph  = inv.get("Portfolio_Health", {})
    rs  = inv.get("Recency_Signal", {})
    hs  = inv.get("Habit_Signal", {})
    vm  = inv.get("Velocity_Metrics", {})
    rel = inv.get("Reliability_Signals", {})

    # normalise wallet share keys  e.g. "Mutual Fund" -> "mutual_fund_pct"
    raw_share = ph.get("Asset_Wallet_Share", {})
    wallet_share = {
        k.lower().replace(" ", "_") + "_pct": r2(v)
        for k, v in raw_share.items()
    }

    # parse tenure string "525 days" -> 525
    tenure_raw = hs.get("Total_Investment_Tenure", "0 days")
    tenure_days = int(tenure_raw.split()[0]) if tenure_raw else None

    # parse avg gap string "2.6 days" -> 2.6
    gap_raw = hs.get("Average_Gap_Between_Actions", "0 days")
    avg_gap = float(gap_raw.split()[0]) if gap_raw and gap_raw != "N/A" else None

    # parse predicted SIP day "Day 10 of month" -> 10
    sip_raw = rel.get("Predicted_SIP_Date", "")
    try:
        predicted_sip_day = int(sip_raw.split()[1])
    except Exception:
        predicted_sip_day = None

    return {
        "portfolio": {
            "total_invested":  r2(ph.get("Total_Invested_Value", 0)),
            "dominant_asset":  ph.get("Dominant_Asset"),
            "wallet_share":    wallet_share,
        },
        "activity": {
            "last_action_date":             rs.get("Last_Activity_Date"),
            "days_since_last_action":       int(rs.get("Days_Since_Last_Action", 0)),
            "status":                       rs.get("Status"),
            "tenure_days":                  tenure_days,
            "avg_gap_between_actions_days": avg_gap,
            "stability_score":              hs.get("Stability_Score"),
        },
        "velocity": {
            "monthly_commitment_l3m":  r2(vm.get("Verified_Monthly_Commitment_L3M", 0)),
            "avg_transaction_size": r2(vm.get("Avg_Transaction_Size", 0)),
        },
        "reliability": {
            "mandate_realization_rate": rel.get("Mandate_Realization_Rate"),
            "predicted_sip_day":        predicted_sip_day,
            "mandate_count":            int(rel.get("Mandate_Frequency_Count", 0)),
            "total_engagement_points":  int(rel.get("Total_Engagement_Points", 0)),
        },
    }


def fmt_insurance(ins: dict):
    if not ins:
        return None
    return {
        "coverage": {
            "total_premium_liability":   r2(ins.get("Total_Premium_Liability", 0)),
            "peak_liability_quarter":    ins.get("Peak_Liability_Quarter"),
            "premium_concentration_index": r2(ins.get("Premium_Concentration_Index", 0)),
        },
        "household": {
            "size":               int(ins.get("Identified_Household_Size", 0)),
            "avg_cost_per_member": r2(ins.get("Avg_Cost_Per_Member", 0)),
        },
        "engagement": {
            "wellness_index_pct":    r2(ins.get("Wellness_Engagement_Index", 0)),
            "health_to_life_ratio":  r2(ins.get("Health_to_Life_Engagement_Ratio", 0)),
        },
    }


def fmt_shopping(shop: dict):
    if not shop:
        return None

    # strip "Rs " prefix and cast to int
    raw_burn = shop.get("Total_Monthly_Burn_L3M", {})
    monthly_burn = {}
    for k, v in raw_burn.items():
        try:
            monthly_burn[k] = int(str(v).replace("Rs", "").strip())
        except Exception:
            monthly_burn[k] = v

    # flatten avg ticket keys
    raw_ticket = shop.get("Avg_Ticket_Credit_vs_UPI", {})
    avg_ticket = {
        "bank_upi":    r2(raw_ticket.get("Bank/UPI")),
        "credit_card": r2(raw_ticket.get("Credit Card")),
    }

    aci = shop.get("Aggregator_Conflict_Index", {})

    return {
        "monthly_burn_l3m": monthly_burn,
        "merchants": {
            "dominant":               shop.get("Dominant_Merchant"),
            "merchants_switch_count":  int(aci.get("Total_Brand_Switches", 0)),
            "merchants_switch_ratio":  r2(aci.get("Switch_Consistency_Ratio", 0)),
        },
        "behavior": {
            "refund_rate_pct":           r2(shop.get("Refund_Rate_Percentage", 0)),
            "weekend_spend_ratio":       r2(shop.get("Weekend_Spend_Ratio", 0)),
            "late_night_orders":         int(shop.get("Late_Night_Order_Count", 0)),
            "payday_splurge_velocity":   r2(shop.get("Payday_Splurge_Velocity", 0)),
            "impulse_purchase_index_pct": r2(shop.get("Impulse_Purchase_Index", 0)),
            "last_30d_order_count":      int(shop.get("Latest_30d_Velocity", 0)),
        },
        "avg_ticket_by_instrument": avg_ticket,
    }


def fmt_unified(uni: dict):
    if not uni:
        return None

    up  = uni.get("Unified_Persona", {})
    cdm = uni.get("Cross_Domain_Metrics", {})
    vhi_raw = cdm.get("Value_Hunting_Intensity", "0%")
    try:
        vhi = float(str(vhi_raw).replace("%", "").strip())
    except Exception:
        vhi = None

    return {
        "segment":                 up.get("Segment"),
        "disposable_income_health": up.get("Disposable_Income_Health"),
        "scores": {
            "future_proof_score":        r2(cdm.get("Future_Proof_Score", 0)),
            "burn_to_build_multiple":    r2(cdm.get("Burn_to_Build_Multiple", 0)),
            "value_hunting_intensity_pct": vhi,
            "liquidity_conflict_risk":   cdm.get("Liquidity_Conflict_Risk"),
        },
    }


def fmt_loan(loan: dict):
    """Format the flat loan-insights dict into a structured response block."""
    if not loan:
        return None
    def _acc(prefix, idx):
        s = f"_acc{idx}"
        acc = {
            "account_id":       loan.get(f"{prefix}{s}"),
            "emi":              r2(loan.get(f"{prefix}{s}_emi")),
            "emi_latest_duedate": loan.get(f"{prefix}{s}_emi_latest_duedate"),
            "max_dpd":          loan.get(f"{prefix}{s}_max_dpd"),
        }
        credit_limit = loan.get(f"{prefix}{s}_max_credit_limit")
        if credit_limit is not None:
            acc["max_credit_limit"] = r2(credit_limit)
        return acc

    def _product(prefix, has_credit_limit=True):
        cnt = loan.get(f"{prefix}_cnt_accounts") or 0
        block = {
            "flag":         loan.get(f"{prefix}_flag"),
            "cnt_accounts": cnt,
            "sms_recency":  loan.get(f"{prefix}_sms_recency"),
            "sms_vintage":  loan.get(f"{prefix}_sms_vintage"),
            "accounts":     [_acc(prefix, i) for i in range(1, cnt + 1)],
        }
        if has_credit_limit:
            block["limit_decrease"]           = loan.get(f"{prefix}_limit_decrease")
            block["limit_decreased_recency"]  = loan.get(f"{prefix}_limit_decreased_recency")
            block["limit_increase"]           = loan.get(f"{prefix}_limit_increase")
            block["limit_increased_recency"]  = loan.get(f"{prefix}_limit_increased_recency")
        return block

    return {
        "delinquency": {
            "cnt_delinquent_c30":    loan.get("cnt_delinquncy_loan_c30"),
            "cnt_delinquent_c60":    loan.get("cnt_delinquncy_loan_c60"),
            "cnt_overdue_senders_c60": loan.get("cnt_overdue_senders_c60"),
        },
        "approvals": {
            "cnt_approved_c30": loan.get("cnt_loan_approved_c30"),
            "cnt_rejected_c30": loan.get("cnt_loan_rejected_c30"),
        },
        "primary_loan_emi": r2(loan.get("emi_loan_acc1")),
        "credit": _product("credit", has_credit_limit=True),
        # "ggives":  _product("ggives",  has_credit_limit=True),
        # "gloan":   _product("gloan",   has_credit_limit=False),
    }


# MASTER FORMATTER
def format_response(meta, promo, banking, invest, insur, shop, unified, loan):
    return sanitize({
        "meta":                 meta,
        "promotional_insights": fmt_promotional(promo) if promo else None,
        "banking_insights":     fmt_banking(banking),
        "investment_insights":  fmt_investment(invest),
        "insurance_insights":   fmt_insurance(insur),
        "shopping_insights":    fmt_shopping(shop),
        "loan_insights": fmt_loan(loan),
        "unified_persona":      fmt_unified(unified),
    })


# ENDPOINT
@app.post("/analyze")
def analyze(request: SMSRequest):
    if not request.sms_data:
        raise HTTPException(status_code=400, detail="sms_data cannot be empty")

    try:
        df_raw = pd.DataFrame(request.sms_data)

        df_promo, df_rest, promo_report = analyze_promotions(df_raw)
        df_tagged = process_sms_df(df_rest)

        df_tagged["date"] = pd.to_datetime(df_tagged["date"], unit="ms", errors="coerce")
        df_raw["date"]    = pd.to_datetime(df_raw["date"],    unit="ms", errors="coerce")

        df_transaction  = analyze_transactions(df_tagged)
        df_investment = parse_investment_sms(df_raw)
        df_insurance  = parse_insurance_sms(df_raw)
        df_shopping   = parse_shopping_sms(df_raw)

        banking_insights = monthly_and_overall_insights(df_transaction) if not df_transaction.empty else {}
        investment_insights  = generate_investment_insights(df_investment)
        insurance_insights   = generate_insurance_insights(df_insurance)
        shopping_insights    = generate_shopping_insights(df_shopping)

        unified_insights = None
        if investment_insights and insurance_insights and shopping_insights:
            unified_insights = generate_unified_persona(
                df_shopping, shopping_insights, insurance_insights, investment_insights
            )

        # Loan insights: generated with realistic random values (no SMS data yet)
        loan_insights = generate_loan_insights()

        meta = build_meta(
            df_raw, df_promo, df_rest, df_tagged,
            investment_insights, insurance_insights, shopping_insights, unified_insights
        )

        return format_response(
            meta, promo_report, banking_insights,
            investment_insights, insurance_insights, shopping_insights, unified_insights,
            loan_insights
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=5004, reload=True)