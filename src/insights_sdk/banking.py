"""
banking.py
----------
Banking insights generator. Self-contained: includes transaction parsing
helpers and banking_summary analysis logic.
"""

import math
import re

import numpy as np
import pandas as pd

from .utils import parse_timestamp, r2


# ---------------------------------------------------------------------------
# Transaction parsing helpers (from transaction.py)
# ---------------------------------------------------------------------------

def clean_text(text):
    if not isinstance(text, str) or pd.isna(text):
        return ""
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r"\bUPI/", "UPI ", text)
    text = re.sub(r"(\d+)(credited|debited)", r"\1 \2", text, flags=re.I)
    text = re.sub(r"(XX\d+)(via)", r"\1 \2", text, flags=re.I)
    text = re.sub(r"(\d+\.\d+)([A-Z]+)", r"\1 \2", text)
    text = re.sub(r'\bBal:\b', r'Bal: ', text, flags=re.I)
    text = re.sub(r'\bRef:\b', r'Ref: ', text, flags=re.I)
    text = re.sub(r'\bno(\d+)\b', r'no \1', text, flags=re.I)
    text = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def first_group(pattern, text, flags=re.I):
    m = re.search(pattern, text, flags)
    if not m:
        return None
    return m.group(1) if m.lastindex else m.group(0)


def extract_reference(text):
    m = re.search(r"([A-Z]{3,6}\d{11}|\b\d{10,12}\b|Ref[:\s-]*(\d+)|UTR[:\s-]*(\d+))", text, re.I)
    if not m:
        return None
    g = m.groups()
    ref = next((x for x in g if x is not None), m.group(0))
    ref = re.sub(r'(Ref|UTR)[:\s-]*', '', ref, flags=re.I).strip()
    return ref or None


def extract_txn_amount(text: str):
    if not isinstance(text, str) or not text.strip():
        return None
    t = text
    _TXN_VERB = r"(?:credited|debited|paid|spent|received|withdrawn|transferred)"
    _CCY = r"(?:rs|inr)\.?"
    _AMT = r"([\d,]+(?:\.\d{1,2})?)"
    _FILLER = r"(?:\s+(?:has\s+been|have\s+been|is|are|was|been|successfully))*"
    amount_patterns = [
        rf"{_CCY}\s*{_AMT}\s*{_FILLER}\s*{_TXN_VERB}\b",
        rf"{_TXN_VERB}\s*(?:by\s*)?{_CCY}\s*{_AMT}\b",
        rf"amount\s+of\s+{_CCY}\s*{_AMT}\s*{_FILLER}\s*{_TXN_VERB}\b",
        rf"\bamt\b[\s:.-]*{_CCY}?\s*{_AMT}\b.*?\b{_TXN_VERB}\b",
    ]
    for p in amount_patterns:
        m = re.search(p, t, re.I)
        if m:
            return m.group(1).replace(",", "")
    return None


def extract_balance(text: str):
    if not isinstance(text, str) or not text.strip():
        return None
    p_balance = (
        r"(?:balance|bal|avl|avail\.bal|avail\s+bal|avl\s+bal)"
        r"[\s\.:]* "
        r"(?:(?:rs|inr)\.?\s*)?"
        r"([\d,]+(?:\.\d{1,2})?)"
    )
    b = first_group(p_balance, text)
    return b.replace(",", "") if b else None


def extract_avl_limit(text: str):
    if not isinstance(text, str) or not text.strip():
        return None
    p = (
        r"(?:avl|avail(?:able)?)\s*li?mi?t[:\s]*"
        r"(?:(?:inr|rs)\.?\s*)?"
        r"([\d,]+(?:\.\d{1,2})?)"
    )
    m = re.search(p, text, re.I)
    if m:
        return m.group(1).replace(",", "")
    return None


def extract_last_bill(text: str):
    if not isinstance(text, str) or not text.strip():
        return None
    patterns = [
        r"total\s+of\s+(?:rs|inr)\.?\s*([\d,]+(?:\.\d{1,2})?)",
        r"total\s+(?:amount\s+)?due[:\s]+(?:(?:rs|inr)\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
        r"bill\s+(?:amount\s+)?(?:of\s+)?(?:(?:rs|inr)\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
        r"amount\s+due[:\s]+(?:(?:rs|inr)\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).replace(",", "")
    return None


def extract_payer_payee(text):
    payer, payee = None, None
    m = re.search(r"UPI/[A-Z0-9]+/(\d+|[A-Z0-9]+)/([A-Z0-9\s*]{3,})", text, re.I)
    if m:
        payee = m.group(2).strip()
    if not payee:
        m = re.search(
            r"(?:to|at|towards|paid\s+to|spent\s+on)\s+([A-Z0-9\s*&]{3,25})"
            r"(?:\s+on|\s+via|\s+Ref|\.|\n|$)", text, re.I
        )
        if m:
            payee = m.group(1).strip()
            payee = re.sub(r"\b(on|via|Ref|RefNo|UPI|account|balance)\b.*", "", payee, flags=re.I).strip()
    m = re.search(
        r"(?:from|by|received\s+from)\s+([A-Z0-9\s*&]{3,25})"
        r"(?:\s+on|\s+via|\s+Ref|\.|\n|$)", text, re.I
    )
    if m:
        payer = m.group(1).strip()
        payer = re.sub(r"\b(on|via|Ref|RefNo|UPI|account|balance)\b.*", "", payer, flags=re.I).strip()
    return payer, payee


def is_salary_credit(text, txn_type):
    if txn_type != "Credit":
        return False
    if not isinstance(text, str):
        return False
    t = text.lower()
    salary_patterns = [
        r"\bsalary\b", r"\bpayroll\b", r"\bstipend\b", r"\bwages\b",
        r"\bmonthly\s+pay\b", r"\bsal\b", r"\bsal\.\b", r"\bsal\s+cr\b", r"\bpay\s+credit\b",
    ]
    return any(re.search(p, t) for p in salary_patterns)


def get_transaction_subtype(text, txn_type, mandate_flag, channel, product):
    t = text.lower()
    if is_salary_credit(text, txn_type):
        return "Salary Credit"
    if re.search(r"\b(refund|reversal|reversed|chargeback|credited\s+back)\b", t):
        return "Refund/Reversal"
    if re.search(r"\b(emi|loan\s+repay|repayment|installment|instalment)\b", t):
        return "EMI/Loan"
    if mandate_flag:
        if re.search(r"\b(failed|declined|unsuccessful|rejected|bounce)\b", t):
            return "Mandate Failed"
        if re.search(r"\b(set\s*up|setup|registered|created|activated|initiation)\b", t):
            return "Mandate Setup"
        return "Mandate Auto"
    if re.search(r"\b(bill|recharge|dth|electricity|utility|broadband|gas|water)\b", t):
        return "Bill Payment"
    if re.search(r"\batm\b", t) and re.search(r"\b(withdrawn|cash)\b", t):
        return "ATM Cash Withdrawal"
    if channel == "Card" and re.search(r"\b(purchase|pos|spent|swipe|merchant)\b", t):
        return "Card Purchase"
    if channel == "UPI":
        return "UPI Transfer"
    if channel in ["NEFT", "IMPS", "Net Banking"]:
        return "Bank Transfer"
    if product == "Credit Card":
        return "Card Transaction"
    return "General"


def parse_transaction(body, address):
    t = clean_text(body)
    p_acc = r"(?:a/c|ac|acc|no|card|wallet|X+|[\*]+)\s*(\d{3,4})\b"
    p_card4 = r"(?:card|ending\s+with)\s*(?:X+|[\*]+)?\s*(\d{4})\b"
    acc = first_group(p_acc, t)
    card4 = first_group(p_card4, t)
    amount = extract_txn_amount(t)
    balance = extract_balance(t)
    card_number = card4 if card4 else (acc if ("card" in t.lower()) else None)
    ref = extract_reference(t)
    mandate_flag = bool(re.search(r"\b(mandate|standing\s+instruction|autopay|si)\b", t, re.I))
    if re.search(r"\b(mandate\s+alert|standing\s+instruction\s+alert)\b", t, re.I):
        txn_type = "Mandate Alert"
    elif re.search(r"\b(mandate\s+initiation|set\s+up\s+mandate|mandate\s+set)\b", t, re.I):
        txn_type = "Mandate"
    elif re.search(r"\b(credited|credit|received|deposited|reversed|reversal)\b", t, re.I):
        txn_type = "Credit"
    elif re.search(r"\b(debited|debit|sent|spent|used|paid|payment\s+of|purchase\s+at)\b", t, re.I):
        txn_type = "Debit"
    else:
        txn_type = "Unknown"
    if re.search(r"\bUPI\b", t, re.I):
        channel = "UPI"
    elif re.search(r"\bneft\b", t, re.I):
        channel = "NEFT"
    elif re.search(r"\bimps\b", t, re.I):
        channel = "IMPS"
    elif re.search(r"\b(card|visa|mastercard|cc|dc|credit\s+card|debit\s+card|XX\d{4})\b", t, re.I):
        channel = "Card"
    elif re.search(r"\b(wallet|rupee|eINR|postpaid|paytm\s+add\s+money|amazon\s+pay|phonepe\s+wallet)\b", t, re.I):
        channel = "Wallet"
    elif re.search(r"\b(neft|imps|rtgs)\b", t, re.I):
        channel = "Net Banking"
    else:
        channel = "Generic"
    if re.search(r"\b(loan|emi)\b", t, re.I):
        product = "Loans"
    elif re.search(r"\b(wallet|rupee|eINR|postpaid|paytm\s+add\s+money|amazon\s+pay|phonepe\s+wallet)\b", t, re.I) or "wallet" in t.lower():
        product = "Wallet"
    elif re.search(r"\b(card|visa|mastercard|cc|dc|credit\s+card|debit\s+card|XX\d{4})\b", t, re.I) or "card" in t.lower():
        product = "Credit Card"
    else:
        product = "Bank Account"
    if re.search(r"\b(refund|reversal|credited\s+back)\b", t, re.I):
        context = "Refund/Reversal"
    elif re.search(r"\b(bill|recharge|dth|electricity|utility)\b", t, re.I):
        context = "Bill Payment"
    elif mandate_flag:
        context = "Mandate Activity"
    elif product == "Credit Card":
        context = "Credit Card Transaction"
    else:
        context = "General Transaction"
    subtype = get_transaction_subtype(t, txn_type, mandate_flag, channel, product)
    payer, payee = extract_payer_payee(t)
    avl_limit_val = extract_avl_limit(t)
    last_bill_val = extract_last_bill(t)
    return {
        "SenderID": address,
        "Financial Product": product,
        "Transaction Type": txn_type,
        "Transaction Subtype": subtype,
        "Amount": amount,
        "Balance": balance,
        "Avl Limit": avl_limit_val,
        "Last Bill": last_bill_val,
        "Payee": payee,
        "Reference Number": ref,
        "Card Number": card_number,
        "Account Number": acc,
        "Transaction Channel": channel,
        "Context": context,
        "Mandate Flag": mandate_flag,
    }


# ---------------------------------------------------------------------------
# Banking summary helpers (from banking_summary.py)
# ---------------------------------------------------------------------------

def prep_txn_df(txn_df: pd.DataFrame) -> pd.DataFrame:
    df = txn_df.copy()
    df["Amount"] = pd.to_numeric(df.get("Amount"), errors="coerce")
    raw_date = df.get("date")
    if pd.api.types.is_datetime64_any_dtype(raw_date):
        df["date_dt"] = raw_date.dt.normalize()
    else:
        df["date_dt"] = raw_date.apply(lambda v: parse_timestamp(v))
        df["date_dt"] = pd.to_datetime(df["date_dt"], errors="coerce").dt.normalize()
    return df


def slice_last_month(df: pd.DataFrame) -> pd.DataFrame:
    today = pd.Timestamp.today().normalize()
    first_day_this_month = today.replace(day=1)
    first_day_last_month = first_day_this_month - pd.offsets.MonthBegin(1)
    return df[(df["date_dt"] >= first_day_last_month) & (df["date_dt"] < first_day_this_month)].copy()


def _clean_id_series(s: pd.Series) -> pd.Series:
    if s is None:
        return pd.Series(dtype="object")
    return (
        s.dropna()
         .astype(str)
         .str.strip()
         .replace(["None", "", "nan", "NaN"], np.nan)
         .dropna()
    )


def compute_num_bank_accounts(df: pd.DataFrame) -> int:
    if df.empty or "Account Number" not in df.columns or "Financial Product" not in df.columns:
        return 0
    bank_like = (df["Financial Product"] != "credit_card")
    return int(_clean_id_series(df.loc[bank_like, "Account Number"]).nunique())


def compute_num_credit_cards_from_accounts(df: pd.DataFrame, num_bank_accounts: int) -> int:
    if df.empty or "Account Number" not in df.columns:
        return 0
    total_unique_account_numbers = int(_clean_id_series(df["Account Number"]).nunique())
    return int(max(total_unique_account_numbers - int(num_bank_accounts), 0))


def cc_like_mask(df: pd.DataFrame) -> pd.Series:
    return (
        (df.get("Financial Product") == "credit_card") |
        (df.get("Context") == "credit_card_transaction") |
        (df.get("Transaction Channel") == "card")
    )


def build_account_details(df: pd.DataFrame) -> tuple:
    bank_details: list = []
    card_details: list = []
    if df.empty:
        return bank_details, card_details

    def _iso(ts):
        try:
            return pd.Timestamp(ts).isoformat() if pd.notna(ts) else None
        except Exception:
            return None

    if "date_dt" not in df.columns:
        df = df.copy()
        raw_date = df.get("date")
        if pd.api.types.is_datetime64_any_dtype(raw_date):
            df["date_dt"] = raw_date.dt.normalize()
        else:
            df["date_dt"] = raw_date.apply(lambda v: parse_timestamp(v))
            df["date_dt"] = pd.to_datetime(df["date_dt"], errors="coerce")

    if "Account Number" not in df.columns:
        return bank_details, card_details

    cleaned = df.copy()
    cleaned["_acct"] = (
        cleaned["Account Number"]
        .astype(str).str.strip()
        .replace(["None", "", "nan", "NaN"], np.nan)
    )
    cleaned = cleaned.dropna(subset=["_acct"])
    cleaned = cleaned.sort_values("date_dt", ascending=False, na_position="last")
    is_cc = cc_like_mask(cleaned)

    bank_rows = cleaned[~is_cc]
    for acct_num, grp in bank_rows.groupby("_acct", sort=False):
        bal_numeric = (
            pd.to_numeric(grp["Balance"], errors="coerce").dropna()
            if "Balance" in grp.columns else pd.Series(dtype=float)
        )
        if not bal_numeric.empty:
            bal_val = float(bal_numeric.iloc[0])
            bal_idx = bal_numeric.index[0]
            bal_date = _iso(grp.at[bal_idx, "date_dt"])
        else:
            bal_val = None
            bal_date = _iso(grp["date_dt"].iloc[0]) if not grp.empty else None
        bank_details.append({
            "account_number": acct_num,
            "balance": {"currency": "INR", "value": bal_val, "updated_at": bal_date},
        })

    cc_rows = cleaned[is_cc]
    for card_num, grp in cc_rows.groupby("_acct", sort=False):
        avl_numeric = (
            pd.to_numeric(grp["Avl Limit"], errors="coerce").dropna()
            if "Avl Limit" in grp.columns else pd.Series(dtype=float)
        )
        bill_numeric = (
            pd.to_numeric(grp["Last Bill"], errors="coerce").dropna()
            if "Last Bill" in grp.columns else pd.Series(dtype=float)
        )
        if "Avl Limit" in grp.columns or "Last Bill" in grp.columns:
            temp = grp[["date_dt"]].copy()
            temp["Avl Limit"] = pd.to_numeric(grp.get("Avl Limit"), errors="coerce")
            temp["Last Bill"] = pd.to_numeric(grp.get("Last Bill"), errors="coerce")
            temp = temp.sort_values("date_dt")
            temp["Avl Limit"] = temp["Avl Limit"].ffill().bfill().fillna(0)
            temp["Last Bill"] = temp["Last Bill"].ffill().bfill().fillna(0)
            temp["Limit"] = temp["Avl Limit"] + temp["Last Bill"]
            if temp["Limit"].max() > 0:
                max_sum = float(temp["Limit"].max())
                max_avl_val = float(math.ceil(max_sum / 1000) * 1000)
                max_avl_idx = temp["Limit"].idxmax()
                max_avl_date = _iso(temp.at[max_avl_idx, "date_dt"])
            else:
                max_avl_val = None
                max_avl_date = None
        else:
            max_avl_val = None
            max_avl_date = None

        if not avl_numeric.empty:
            latest_avl_val = float(avl_numeric.iloc[0])
            latest_avl_idx = avl_numeric.index[0]
            latest_avl_date = _iso(grp.at[latest_avl_idx, "date_dt"])
        else:
            latest_avl_val = None
            latest_avl_date = None

        if not bill_numeric.empty:
            last_bill_val = float(bill_numeric.iloc[0])
            last_bill_idx = bill_numeric.index[0]
            last_bill_date = _iso(grp.at[last_bill_idx, "date_dt"])
        else:
            last_bill_val = None
            last_bill_date = None

        if last_bill_val is not None and max_avl_val and max_avl_val > 0:
            utilisation_pct = round(last_bill_val / max_avl_val, 4)
        else:
            utilisation_pct = None

        card_details.append({
            "credit_card_number": card_num,
            "balance": {"currency": "INR", "value": latest_avl_val, "updated_at": latest_avl_date},
            "last_bill": {"currency": "INR", "value": last_bill_val, "updated_at": last_bill_date},
            "credit_limit": {"currency": "INR", "value": max_avl_val, "updated_at": max_avl_date},
            "utilisation_pct": utilisation_pct,
        })

    return bank_details, card_details


def sum_amount(df: pd.DataFrame, mask: pd.Series) -> float:
    if df.empty:
        return 0.0
    x = df.loc[mask, "Amount"].sum(min_count=1)
    return float(x) if pd.notna(x) else 0.0


def count_rows(mask: pd.Series) -> int:
    return int(mask.sum()) if mask is not None else 0


def safe_div(n: float, d: int, default=np.nan):
    return default if d == 0 else (n / d)


def compute_spend_earn(df: pd.DataFrame) -> dict:
    if df.empty or "Transaction Type" not in df.columns or "Amount" not in df.columns:
        return {
            "spend_total": 0.0, "earn_total": 0.0,
            "spend_txn_count": 0, "earn_txn_count": 0,
            "avg_spend_per_txn": np.nan, "avg_earn_per_txn": np.nan,
        }
    amount_pos = df["Amount"].fillna(0) > 0
    spend_mask = df["Transaction Type"].isin(["debit", "mandate"]) & amount_pos
    earn_mask = (df["Transaction Type"] == "credit") & amount_pos
    spend_total = sum_amount(df, spend_mask)
    earn_total = sum_amount(df, earn_mask)
    spend_txn_count = count_rows(spend_mask)
    earn_txn_count = count_rows(earn_mask)
    return {
        "spend_total": spend_total,
        "earn_total": earn_total,
        "spend_txn_count": spend_txn_count,
        "earn_txn_count": earn_txn_count,
        "avg_spend_per_txn": safe_div(spend_total, spend_txn_count, default=np.nan),
        "avg_earn_per_txn": safe_div(earn_total, earn_txn_count, default=np.nan),
    }


def compute_upi_metrics(df: pd.DataFrame) -> dict:
    if df.empty or "Transaction Channel" not in df.columns or "Transaction Type" not in df.columns or "Amount" not in df.columns:
        return {"upi_spend_total": 0.0, "upi_spend_txn_count": 0, "upi_ticket_size": np.nan}
    amount_pos = df["Amount"].fillna(0) > 0
    mask = (
        (df["Transaction Channel"] == "upi") &
        (df["Transaction Type"] == "debit") &
        amount_pos
    )
    upi_spend_total = sum_amount(df, mask)
    upi_spend_txn_count = count_rows(mask)
    upi_ticket_size = safe_div(upi_spend_total, upi_spend_txn_count, default=np.nan)
    return {
        "upi_spend_total": upi_spend_total,
        "upi_spend_txn_count": upi_spend_txn_count,
        "upi_ticket_size": upi_ticket_size,
    }


def compute_cc_metrics(df: pd.DataFrame, num_credit_cards: int) -> dict:
    if num_credit_cards == 0:
        return {"num_credit_cards": 0, "cc_spend_total": 0.0, "cc_spend_txn_count": 0, "cc_ticket_size": 0.0}
    if df.empty or "Transaction Type" not in df.columns or "Amount" not in df.columns:
        return {"num_credit_cards": int(num_credit_cards), "cc_spend_total": 0.0, "cc_spend_txn_count": 0, "cc_ticket_size": 0.0}
    amount_pos = df["Amount"].fillna(0) > 0
    mask = cc_like_mask(df) & (df["Transaction Type"] == "debit") & amount_pos
    cc_spend_total = sum_amount(df, mask)
    cc_spend_txn_count = count_rows(mask)
    cc_ticket_size = safe_div(cc_spend_total, cc_spend_txn_count, default=np.nan)
    return {
        "num_credit_cards": int(num_credit_cards),
        "cc_spend_total": cc_spend_total,
        "cc_spend_txn_count": cc_spend_txn_count,
        "cc_ticket_size": (cc_ticket_size if cc_spend_txn_count else 0.0),
    }


def compute_top_channel(df: pd.DataFrame, num_credit_cards: int) -> str | None:
    if df.empty or "Transaction Channel" not in df.columns:
        return None
    df2 = df.copy()
    if num_credit_cards == 0:
        df2 = df2.loc[~cc_like_mask(df2)]
        df2 = df2[df2["Transaction Channel"] != "card"]
    vc = df2["Transaction Channel"].value_counts(dropna=True)
    if vc.empty:
        return None
    for ch in vc.index.tolist():
        if ch != "generic":
            return ch
    return vc.index[0]


def build_insights(df: pd.DataFrame, force_num_credit_cards: int = None) -> dict:
    out = {}
    num_bank_accounts = compute_num_bank_accounts(df)
    if force_num_credit_cards is not None:
        num_credit_cards = force_num_credit_cards
    else:
        num_credit_cards = compute_num_credit_cards_from_accounts(df, num_bank_accounts)
    out["num_bank_accounts"] = int(num_bank_accounts)
    out["num_credit_cards"] = int(num_credit_cards)
    out.update(compute_spend_earn(df))
    out.update(compute_upi_metrics(df))
    out.update(compute_cc_metrics(df, out["num_credit_cards"]))
    out["top_channel"] = compute_top_channel(df, out["num_credit_cards"])
    return out


def monthly_and_overall_insights(txn_df: pd.DataFrame) -> dict:
    df = prep_txn_df(txn_df)
    overall = build_insights(df)
    last_month_df = slice_last_month(df)
    force_cc = None
    if overall.get("num_credit_cards", 0) == 0:
        force_cc = 0
    last_month = build_insights(last_month_df, force_num_credit_cards=force_cc)
    bank_account_details, credit_card_details = build_account_details(df)
    return {
        "last_month": last_month,
        "overall": overall,
        "last_month_rows": int(len(last_month_df)),
        "overall_rows": int(len(df)),
        "bank_account_details": bank_account_details,
        "credit_card_details": credit_card_details,
    }


# ---------------------------------------------------------------------------
# Column mapping: feature_store dict keys -> DataFrame column names
# ---------------------------------------------------------------------------

_FIELD_TO_COL = {
    "txn_type": "Transaction Type",
    "txn_subtype": "Transaction Subtype",
    "amount": "Amount",
    "balance": "Balance",
    "avl_limit": "Avl Limit",
    "last_bill": "Last Bill",
    "account_number": "Account Number",
    "card_number": "Card Number",
    "financial_product": "Financial Product",
    "txn_channel": "Transaction Channel",
    "reference_number": "Reference Number",
    "payee": "Payee",
    "context": "Context",
    "mandate_flag": "Mandate Flag",
    "sender_address": "SenderID",
    "raw_body": "body",
    "entity_name": "entity_name",
    "timestamp": "date",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_banking_insights(feature_store: list[dict]) -> dict | None:
    """Generate banking insights from the feature store.

    Filters for sms_category == 'Transactions', builds a DataFrame,
    runs the full banking_summary pipeline, and outputs the final shape
    (incorporating the fmt_banking formatting).
    """
    txn_dicts = [d for d in feature_store if d.get("sms_category") == "transactions"]
    if not txn_dicts:
        return None

    # Build DataFrame with expected column names
    rows = []
    for d in txn_dicts:
        row = {}
        for src_key, col_name in _FIELD_TO_COL.items():
            row[col_name] = d.get(src_key)
        rows.append(row)

    txn_df = pd.DataFrame(rows)
    if txn_df.empty:
        return None

    # Run the full analysis pipeline
    b = monthly_and_overall_insights(txn_df)
    if not b:
        return None

    # --- Format into final shape (merged fmt_banking logic) ---

    def _window(data, rows_count):
        return {
            "rows_analyzed": rows_count,
            "spend": {
                "total": r2(data.get("spend_total", 0)),
                "txn_count": int(data.get("spend_txn_count", 0)),
                "avg_per_txn": r2(data.get("avg_spend_per_txn")),
            },
            "earn": {
                "total": r2(data.get("earn_total", 0)),
                "txn_count": int(data.get("earn_txn_count", 0)),
                "avg_per_txn": r2(data.get("avg_earn_per_txn")),
            },
            "top_channel": data.get("top_channel"),
        }

    def _channel(data):
        return {
            "upi": {
                "spend_total": r2(data.get("upi_spend_total", 0)),
                "txn_count": int(data.get("upi_spend_txn_count", 0)),
                "avg_ticket": r2(data.get("upi_ticket_size")),
            },
            "credit_card": {
                "spend_total": r2(data.get("cc_spend_total", 0)),
                "txn_count": int(data.get("cc_spend_txn_count", 0)),
                "avg_ticket": r2(data.get("cc_ticket_size")),
            },
        }

    overall = b.get("overall", {})
    last_month = b.get("last_month", {})

    bank_details = b.get("bank_account_details", [])
    raw_card_details = b.get("credit_card_details", [])

    # Filter credit cards: prefer cards with actual values
    cards_with_values = []
    cards_empty = []
    for c in raw_card_details:
        v_bal = c.get("balance", {}).get("value")
        v_bill = c.get("last_bill", {}).get("value")
        v_limit = c.get("credit_limit", {}).get("value")
        if v_bal is not None or v_bill is not None or v_limit is not None:
            cards_with_values.append(c)
        else:
            cards_empty.append(c)

    est_total_cc = int(overall.get("num_credit_cards", 0))
    target_count = max(len(cards_with_values), est_total_cc)
    final_cards = cards_with_values[:]
    if len(final_cards) < target_count:
        needed = target_count - len(final_cards)
        final_cards.extend(cards_empty[:needed])

    return {
        "accounts": {
            "bank_accounts": {
                "total": int(overall.get("num_bank_accounts", 0)),
                "details": bank_details,
            },
            "credit_cards": {
                "total": len(final_cards),
                "details": final_cards,
            },
        },
        "cash_flow": {
            "overall": _window(overall, b.get("overall_rows", 0)),
            "last_month": _window(last_month, b.get("last_month_rows", 0)),
        },
        "channel_breakdown": {
            "overall": _channel(overall),
            "last_month": _channel(last_month),
        },
    }
