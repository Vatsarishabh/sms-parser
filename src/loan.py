"""
loan.py
-------
Since real loan SMS data is not yet available, this module generates
realistic *random* values for all Loan-domain features.

Call `generate_loan_insights()` to get a dictionary whose keys match
the feature names used downstream (and documented in the schema below).

Feature reference
-----------------
cnt_delinquncy_loan_c30      – count of distinct loan accounts delinquent in current 30 days
cnt_delinquncy_loan_c60      – count of distinct loan accounts delinquent in current 60 days
cnt_loan_approved_c30        – Number of loans approved in the last 30 days
cnt_loan_rejected_c30        – Number of loans rejected in the last 30 days
cnt_overdue_senders_c60      – Count of bill-overdue distinct senders – last 60 days

gcredit_*                    – features for up to 3 Gcredit accounts
ggives_*                     – features for up to 3 Ggives accounts
gloan_*                      – features for up to 3 Gloan accounts
"""

import random
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_account_id(prefix: str, idx: int) -> str:
    """Return a masked account-like identifier, e.g. 'GCRD-****1234'."""
    suffix = random.randint(1000, 9999)
    return f"{prefix}-****{suffix}"


def _random_emi() -> float:
    """Return a realistic EMI amount (INR)."""
    return round(random.uniform(500, 25000), 2)


def _random_credit_limit() -> float:
    """Return a realistic credit/loan limit (INR)."""
    return round(random.choice([
        5000, 10000, 15000, 20000, 25000, 30000,
        40000, 50000, 75000, 100000, 150000, 200000,
    ]) * random.uniform(0.9, 1.1), 2)


def _random_dpd() -> int:
    """Days Past Due – 0 means on-time; higher values indicate delinquency."""
    return random.choices([0, 0, 0, 7, 15, 30, 45, 60, 90], weights=[40, 15, 10, 10, 8, 7, 5, 3, 2])[0]


def _random_due_date() -> str:
    """Return a future due date as an ISO-8601 string."""
    days_ahead = random.randint(1, 45)
    due = date.today() + timedelta(days=days_ahead)
    return due.isoformat()


def _random_recency() -> int:
    """Days since last SMS / event (1 – 180)."""
    return random.randint(1, 180)


def _random_vintage() -> int:
    """Days since first SMS / event (30 – 730)."""
    return random.randint(30, 730)


def _random_flag() -> int:
    """Binary flag: 0 or 1, weighted towards 1 (user has the product)."""
    return random.choices([0, 1], weights=[20, 80])[0]


def _random_limit_flag() -> int:
    """Binary flag for limit change events (less common)."""
    return random.choices([0, 1], weights=[70, 30])[0]


def _random_limit_change_recency() -> int | None:
    """Days since last limit change; None if the change never happened."""
    return random.randint(1, 365) if random.random() > 0.4 else None


# ---------------------------------------------------------------------------
# Per-account block builder
# ---------------------------------------------------------------------------

def _build_account_block(prefix: str, acc_idx: int, has_credit_limit: bool = True) -> dict:
    """
    Build a dictionary of features for a single loan/credit account.

    Parameters
    ----------
    prefix        : product prefix, e.g. 'gcredit', 'ggives', 'gloan'
    acc_idx       : account rank (1, 2, 3)
    has_credit_limit : Gloan accounts do not expose a credit-limit field.
    """
    suffix = f"_acc{acc_idx}"
    block = {
        f"{prefix}{suffix}":                    _random_account_id(prefix.upper(), acc_idx),
        f"{prefix}{suffix}_emi":                _random_emi(),
        f"{prefix}{suffix}_emi_latest_duedate": _random_due_date(),
        f"{prefix}{suffix}_max_dpd":            _random_dpd(),
    }
    if has_credit_limit:
        block[f"{prefix}{suffix}_max_credit_limit"] = _random_credit_limit()
    return block


# ---------------------------------------------------------------------------
# Per-product block builder
# ---------------------------------------------------------------------------

def _build_product_block(prefix: str, has_credit_limit: bool = True) -> dict:
    """
    Build all features for a 3-account product (gcredit / ggives / gloan).

    Consistency rules
    -----------------
    * flag = 0  →  product not used: cnt_accounts=0, no SMS, no EMI, no
                   limit-change events (all None).  No account sub-blocks.
    * flag = 1  →  product is active: cnt_accounts is at least 1 (1 here
                   since user capped at 1); SMS recency & vintage are
                   meaningful; limit-change events are possible.
    """
    flag = _random_flag()

    if not flag:
        # Product not used – everything is absent / zero
        block: dict = {
            f"{prefix}_flag":         0,
            f"{prefix}_cnt_accounts": 0,
            f"{prefix}_sms_recency":  None,
            f"{prefix}_sms_vintage":  None,
        }
        if has_credit_limit:
            block.update({
                f"{prefix}_limit_decrease":          0,
                f"{prefix}_limit_decreased_recency": None,
                f"{prefix}_limit_increase":          0,
                f"{prefix}_limit_increased_recency": None,
            })
        return block

    # flag = 1: at least 1 account must exist
    cnt_accounts = random.randint(1, 3)   # capped at 1 per user config

    block = {
        f"{prefix}_flag":         1,
        f"{prefix}_cnt_accounts": cnt_accounts,
        f"{prefix}_sms_recency":  _random_recency(),
        f"{prefix}_sms_vintage":  _random_vintage(),
    }

    # Limit-change features (gcredit & ggives only) – only possible when active
    if has_credit_limit:
        limit_dec = _random_limit_flag()
        limit_inc = _random_limit_flag()
        block.update({
            f"{prefix}_limit_decrease":          limit_dec,
            f"{prefix}_limit_decreased_recency": _random_limit_change_recency() if limit_dec else None,
            f"{prefix}_limit_increase":          limit_inc,
            f"{prefix}_limit_increased_recency": _random_limit_change_recency() if limit_inc else None,
        })

    # Account-level details – only for accounts that exist
    for i in range(1, cnt_accounts + 1):
        block.update(_build_account_block(prefix, i, has_credit_limit=has_credit_limit))

    return block


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_loan_insights() -> dict:
    """
    Return a flat dictionary of all Loan-domain features with random
    but realistic values.

    Consistency model
    -----------------
    1. Build the three branded product blocks first — they determine which
       accounts exist and what their EMIs are.
    2. `emi_loan_acc1` (primary loan EMI) is NOT a separate random value.
       It is taken directly from the first active product's acc1 EMI, so
       it is always consistent with the accounts that exist.
    3. Delinquency, overdue, approval / rejection counts are all bounded
       by the total number of active accounts — you cannot be delinquent
       on an account you don't have.
    """
    insights: dict = {}

    # ── Step 1: build branded product blocks ─────────────────────────────────
    gcredit_block = _build_product_block("gcredit", has_credit_limit=True)
    ggives_block  = _build_product_block("ggives",  has_credit_limit=True)
    gloan_block   = _build_product_block("gloan",   has_credit_limit=False)

    insights.update(gcredit_block)
    insights.update(ggives_block)
    insights.update(gloan_block)

    # ── Step 2: derive totals from actual account data ────────────────────────
    total_accounts = (
        gcredit_block.get("gcredit_cnt_accounts", 0) +
        ggives_block.get("ggives_cnt_accounts",   0) +
        gloan_block.get("gloan_cnt_accounts",     0)
    )
    any_active = total_accounts > 0

    # ── Step 3: primary loan EMI = acc1 EMI of first active product ───────────
    # This avoids a phantom 4th independent EMI that has no backing account.
    primary_emi = None
    for prefix in ("gcredit", "ggives", "gloan"):
        if insights.get(f"{prefix}_flag") == 1:
            primary_emi = insights.get(f"{prefix}_acc1_emi")
            break
    insights["emi_loan_acc1"] = primary_emi

    # ── Step 4: delinquency / overdue – bounded by active accounts ────────────
    if not any_active:
        # No accounts → nothing can be delinquent or overdue
        insights["cnt_delinquncy_loan_c30"] = 0
        insights["cnt_delinquncy_loan_c60"] = 0
        insights["cnt_overdue_senders_c60"] = 0
        insights["cnt_loan_approved_c30"]   = 0
        insights["cnt_loan_rejected_c30"]   = 0
    else:
        # Delinquent accounts cannot exceed total accounts
        c30 = random.randint(0, min(total_accounts, 2))
        c60 = random.randint(c30, min(total_accounts, c30 + 1))   # c60 >= c30
        insights["cnt_delinquncy_loan_c30"] = c30
        insights["cnt_delinquncy_loan_c60"] = c60
        insights["cnt_overdue_senders_c60"] = random.randint(0, min(total_accounts, 2))
        # Approvals / rejections: loan applications in window (≥1 since user is active)
        insights["cnt_loan_approved_c30"]   = random.randint(0, 2)
        insights["cnt_loan_rejected_c30"]   = random.randint(0, 1)

    return insights
