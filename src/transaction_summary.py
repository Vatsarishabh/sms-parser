import math
import numpy as np
import pandas as pd

# =========================
# 1) PREP + WINDOWING
# =========================
def prep_txn_df(txn_df: pd.DataFrame) -> pd.DataFrame:
    """
    - Amount -> numeric
    - date_dt -> normalized datetime from epoch ms 'date'
    """
    df = txn_df.copy()
    df["Amount"] = pd.to_numeric(df.get("Amount"), errors="coerce")
    df["date_dt"] = pd.to_datetime(df.get("date"), unit="ms", errors="coerce").dt.normalize()
    return df


def slice_last_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns dataframe for last calendar month based on df['date_dt'].
    """
    today = pd.Timestamp.today().normalize()
    first_day_this_month = today.replace(day=1)
    first_day_last_month = first_day_this_month - pd.offsets.MonthBegin(1)
    return df[(df["date_dt"] >= first_day_last_month) & (df["date_dt"] < first_day_this_month)].copy()


# =========================
# 2) ID HELPERS
# =========================
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


# =========================
# 3) BANK + CARD COUNT (NO EXTRA FEATURES RETURNED)
# =========================
def compute_num_bank_accounts(df: pd.DataFrame) -> int:
    """
    bank_acct_like = Financial Product != 'Credit Card'
    num_bank_accounts = unique Account Number count among bank-like rows
    """
    if df.empty or "Account Number" not in df.columns or "Financial Product" not in df.columns:
        return 0

    bank_like = (df["Financial Product"] != "Credit Card")
    return int(_clean_id_series(df.loc[bank_like, "Account Number"]).nunique())


def compute_num_credit_cards_from_accounts(df: pd.DataFrame, num_bank_accounts: int) -> int:
    """
    Uses your 'above logic' BUT DOES NOT RETURN:
      total_unique_account_numbers
      remaining_accounts_est

    num_credit_cards = max(total_unique_account_numbers - num_bank_accounts, 0)

    NOTE: This is an estimate if your 'Account Number' column mixes bank A/C and card last4 etc.
    """
    if df.empty or "Account Number" not in df.columns:
        return 0

    total_unique_account_numbers = int(_clean_id_series(df["Account Number"]).nunique())
    return int(max(total_unique_account_numbers - int(num_bank_accounts), 0))


def cc_like_mask(df: pd.DataFrame) -> bool:
    """
    Rows that look like they belong to credit card activity.
    """
    return (
        (df.get("Financial Product") == "Credit Card") |
        (df.get("Context") == "Credit Card Transaction") |
        (df.get("Transaction Channel") == "Card")
    )


# =========================
# 3b) ACCOUNT / CARD DETAILS
# =========================
def build_account_details(df: pd.DataFrame) -> tuple:
    """
    Returns (bank_account_details, credit_card_details).

    Bank account schema:
      {
        "account_number": str,
        "balance": {"currency": "INR", "value": float|None, "updated_at": str|None}
      }

    Credit card schema:
      {
        "credit_card_number": str,
        "balance":        {"currency": "INR", "value": float|None, "updated_at": str|None},
        "last_bill":      {"currency": "INR", "value": float|None, "updated_at": str|None},
        "credit_limit":   {"currency": "INR", "value": float|None, "updated_at": str|None},
        "utilisation_pct": float|None
      }

    Strategy:
      balance.value      = MAX 'Avl Limit' seen for that card
      last_bill.value    = 'Last Bill' from most-recent statement SMS
      credit_limit.value = same MAX Avl Limit (best SMS proxy)
      utilisation_pct    = last_bill / credit_limit
    """
    bank_details: list = []
    card_details: list = []

    if df.empty:
        return bank_details, card_details

    # helpers
    def _to_float(v):
        try:
            f = float(str(v).replace(",", ""))
            return f if pd.notna(f) else None
        except Exception:
            return None

    def _iso(ts):
        try:
            return pd.Timestamp(ts).isoformat() if pd.notna(ts) else None
        except Exception:
            return None

    # ensure date_dt exists
    if "date_dt" not in df.columns:
        df = df.copy()
        df["date_dt"] = pd.to_datetime(df.get("date"), unit="ms", errors="coerce")

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
    is_cc   = cc_like_mask(cleaned)

    # ── BANK ACCOUNTS: group all rows, pick last-known non-null balance ───────
    bank_rows = cleaned[~is_cc]
    for acct_num, grp in bank_rows.groupby("_acct", sort=False):
        # grp is already sorted newest-first
        bal_numeric = (
            pd.to_numeric(grp["Balance"], errors="coerce").dropna()
            if "Balance" in grp.columns else pd.Series(dtype=float)
        )
        if not bal_numeric.empty:
            # most-recent row that actually reported a balance
            bal_val  = float(bal_numeric.iloc[0])
            bal_idx  = bal_numeric.index[0]
            bal_date = _iso(grp.at[bal_idx, "date_dt"])
        else:
            bal_val  = None
            bal_date = _iso(grp["date_dt"].iloc[0]) if not grp.empty else None

        bank_details.append({
            "account_number": acct_num,
            "balance": {
                "currency":   "INR",
                "value":      bal_val,
                "updated_at": bal_date,
            },
        })

    # credit cards: aggregate across all rows per card number
    cc_rows = cleaned[is_cc]
    for card_num, grp in cc_rows.groupby("_acct", sort=False):
        # grp is newest-first

        # credit_limit = MAX Avl Limit ever seen (historical peak = best proxy for true limit)
        # balance      = LATEST non-null Avl Limit (current available balance)
        avl_numeric = (
            pd.to_numeric(grp["Avl Limit"], errors="coerce").dropna()
            if "Avl Limit" in grp.columns else pd.Series(dtype=float)
        )
        if not avl_numeric.empty:
            # credit_limit: max across all history
            max_avl_val  = float(avl_numeric.max())
            max_avl_val = math.ceil(max_avl_val / 1000) * 1000
            max_avl_idx  = avl_numeric.idxmax()
            max_avl_date = _iso(grp.at[max_avl_idx, "date_dt"])
            # balance: most-recent reported avl limit (iloc[0] = newest-first)
            latest_avl_val  = float(avl_numeric.iloc[0])
            latest_avl_idx  = avl_numeric.index[0]
            latest_avl_date = _iso(grp.at[latest_avl_idx, "date_dt"])
        else:
            max_avl_val     = None
            max_avl_date    = None
            latest_avl_val  = None
            latest_avl_date = None

        # last_bill = most-recent non-null Last Bill
        bill_numeric = (
            pd.to_numeric(grp["Last Bill"], errors="coerce").dropna()
            if "Last Bill" in grp.columns else pd.Series(dtype=float)
        )
        if not bill_numeric.empty:
            last_bill_val  = float(bill_numeric.iloc[0])
            last_bill_idx  = bill_numeric.index[0]
            last_bill_date = _iso(grp.at[last_bill_idx, "date_dt"])
        else:
            last_bill_val  = None
            last_bill_date = None

        # utilisation = last_bill / credit_limit
        if last_bill_val is not None and max_avl_val and max_avl_val > 0:
            utilisation_pct = round(last_bill_val / max_avl_val, 4)
        else:
            utilisation_pct = None

        card_details.append({
            "credit_card_number": card_num,
            "balance": {
                "currency":   "INR",
                "value":      latest_avl_val,   # most-recent available balance
                "updated_at": latest_avl_date,
            },
            "last_bill": {
                "currency":   "INR",
                "value":      last_bill_val,
                "updated_at": last_bill_date,
            },
            "credit_limit": {
                "currency":   "INR",
                "value":      max_avl_val,       # historical max = true limit proxy
                "updated_at": max_avl_date,
            },
            "utilisation_pct": utilisation_pct,
        })

    return bank_details, card_details


# =========================
# 4) BASIC METRIC HELPERS
# =========================
def sum_amount(df: pd.DataFrame, mask: pd.Series) -> float:
    if df.empty:
        return 0.0
    x = df.loc[mask, "Amount"].sum(min_count=1)
    return float(x) if pd.notna(x) else 0.0


def count_rows(mask: pd.Series) -> int:
    return int(mask.sum()) if mask is not None else 0


def safe_div(n: float, d: int, default=np.nan):
    return default if d == 0 else (n / d)


# =========================
# 5) CORE FEATURE BLOCKS
# =========================
def compute_spend_earn(df: pd.DataFrame) -> dict:
    """
    FIX:
    - spend/earn counts only include rows with Amount > 0
      so if earn_total is 0 => earn_txn_count becomes 0
    """
    if df.empty or "Transaction Type" not in df.columns or "Amount" not in df.columns:
        return {
            "spend_total": 0.0, "earn_total": 0.0,
            "spend_txn_count": 0, "earn_txn_count": 0,
            "avg_spend_per_txn": np.nan, "avg_earn_per_txn": np.nan
        }

    amount_pos = df["Amount"].fillna(0) > 0

    spend_mask = df["Transaction Type"].isin(["Debit", "Mandate"]) & amount_pos
    earn_mask  = (df["Transaction Type"] == "Credit") & amount_pos

    spend_total = sum_amount(df, spend_mask)
    earn_total  = sum_amount(df, earn_mask)

    spend_txn_count = count_rows(spend_mask)
    earn_txn_count  = count_rows(earn_mask)

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
        return {
            "upi_spend_total": 0.0,
            "upi_spend_txn_count": 0,
            "upi_ticket_size": np.nan,
        }

    amount_pos = df["Amount"].fillna(0) > 0
    mask = (
        (df["Transaction Channel"] == "UPI") &
        (df["Transaction Type"] == "Debit") &
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
    """
    HARD RULE:
    - if num_credit_cards == 0 => cc spend metrics forced to 0
    - cc spend only counts Amount > 0
    """
    if num_credit_cards == 0:
        return {
            "num_credit_cards": 0,
            "cc_spend_total": 0.0,
            "cc_spend_txn_count": 0,
            "cc_ticket_size": 0.0,
        }

    if df.empty or "Transaction Type" not in df.columns or "Amount" not in df.columns:
        return {
            "num_credit_cards": int(num_credit_cards),
            "cc_spend_total": 0.0,
            "cc_spend_txn_count": 0,
            "cc_ticket_size": 0.0,
        }

    amount_pos = df["Amount"].fillna(0) > 0
    mask = cc_like_mask(df) & (df["Transaction Type"] == "Debit") & amount_pos

    cc_spend_total = sum_amount(df, mask)
    cc_spend_txn_count = count_rows(mask)
    cc_ticket_size = safe_div(cc_spend_total, cc_spend_txn_count, default=np.nan)

    return {
        "num_credit_cards": int(num_credit_cards),
        "cc_spend_total": cc_spend_total,
        "cc_spend_txn_count": cc_spend_txn_count,
        "cc_ticket_size": (cc_ticket_size if cc_spend_txn_count else 0.0),
    }


def compute_top_channel(df: pd.DataFrame, num_credit_cards: int) -> str:
    """
    RULES:
    - top_channel cannot be 'Generic' if any other exists
    - if num_credit_cards == 0 => 'Card' cannot be top_channel
      and we exclude cc-like rows from channel competition
    """
    if df.empty or "Transaction Channel" not in df.columns:
        return None

    df2 = df.copy()

    if num_credit_cards == 0:
        # remove CC-like rows so "Card" doesn't win by volume even when it's fake/absent
        df2 = df2.loc[~cc_like_mask(df2)]
        df2 = df2[df2["Transaction Channel"] != "Card"]

    vc = df2["Transaction Channel"].value_counts(dropna=True)
    if vc.empty:
        return None

    for ch in vc.index.tolist():
        if ch != "Generic":
            return ch

    return vc.index[0]


# =========================
# 6) INSIGHTS (ONE WINDOW)
# =========================
def build_insights(df: pd.DataFrame, force_num_credit_cards: int = None) -> dict:
    """
    OUTPUT FEATURES ONLY:
      - num_bank_accounts
      - num_credit_cards (computed using num_bank_accounts + total unique account numbers internally or forced)
      - spend/earn
      - upi metrics
      - cc metrics (zeroed if num_credit_cards==0)
      - top_channel (not Generic; not Card if num_credit_cards==0)
    """
    out = {}

    # bank + cards (but DO NOT OUTPUT total_unique_account_numbers / remaining_accounts_est)
    num_bank_accounts = compute_num_bank_accounts(df)
    if force_num_credit_cards is not None:
        num_credit_cards = force_num_credit_cards
    else:
        num_credit_cards = compute_num_credit_cards_from_accounts(df, num_bank_accounts)

    out["num_bank_accounts"] = int(num_bank_accounts)
    out["num_credit_cards"] = int(num_credit_cards)

    # spend/earn
    out.update(compute_spend_earn(df))

    # UPI
    out.update(compute_upi_metrics(df))

    # CC metrics (enforce your rule)
    out.update(compute_cc_metrics(df, out["num_credit_cards"]))

    # top channel
    out["top_channel"] = compute_top_channel(df, out["num_credit_cards"])

    return out


# =========================
# 7) MONTHLY + OVERALL
# =========================
def monthly_and_overall_insights(txn_df: pd.DataFrame) -> dict:
    """
    Returns:
      {
        "last_month": {...features...},
        "overall": {...features...},
        "last_month_rows": int,
        "overall_rows": int
      }
    """
    df = prep_txn_df(txn_df)

    # 1. Calculate overall insights first (ground truth for cards)
    overall = build_insights(df)

    # 2. Slice for last month
    last_month_df = slice_last_month(df)

    # 3. Apply HARD RULE: If overall CC count is 0, last month must be 0
    force_cc = None
    if overall.get("num_credit_cards", 0) == 0:
        force_cc = 0

    last_month = build_insights(last_month_df, force_num_credit_cards=force_cc)

    # 4. Account / card details (latest balance + updated_at per unique number)
    bank_account_details, credit_card_details = build_account_details(df)

    return {
        "last_month":           last_month,
        "overall":              overall,
        "last_month_rows":      int(len(last_month_df)),
        "overall_rows":         int(len(df)),
        "bank_account_details": bank_account_details,
        "credit_card_details":  credit_card_details,
    }