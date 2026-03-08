"""
lending.py
----------
Lending / loan insights generator.
Returns None when no lending SMS data exists — no random/fake data.
"""

from .utils import r2


def generate_lending_insights(feature_store: list[dict]) -> dict | None:
    """Generate lending insights from the feature store.

    Filters for sms_category == 'Lending'. Returns None if no lending SMS exist.
    """
    lending_dicts = [d for d in feature_store if d.get("sms_category") == "lending"]
    if not lending_dicts:
        return None

    has_event = any(d.get("event_type") for d in lending_dicts)
    if not has_event:
        return None

    # Extract real data from parsed lending SMS
    loan_accounts = {d["loan_account"] for d in lending_dicts if d.get("loan_account")}
    total_loans = len(loan_accounts)

    # Primary EMI
    emi_amounts = [d["emi_amount"] for d in lending_dicts if d.get("emi_amount") is not None]
    primary_emi = r2(emi_amounts[0]) if emi_amounts else None

    # Delinquency
    overdue_count = sum(1 for d in lending_dicts if d.get("is_overdue"))

    # Approvals / rejections
    approved = sum(1 for d in lending_dicts if d.get("event_type") == "approved")
    rejected = sum(1 for d in lending_dicts if d.get("event_type") == "rejected")

    # Build per-account details
    accounts = []
    for i, acc_id in enumerate(sorted(loan_accounts), 1):
        acc_msgs = [d for d in lending_dicts if d.get("loan_account") == acc_id]
        acc_emi = next((d["emi_amount"] for d in acc_msgs if d.get("emi_amount")), None)
        acc_due = next((d["due_date"] for d in acc_msgs if d.get("due_date")), None)
        acc_overdue = any(d.get("is_overdue") for d in acc_msgs)
        acc_outstanding = next((d["outstanding"] for d in acc_msgs if d.get("outstanding")), None)

        accounts.append({
            "account_id": acc_id,
            "emi": r2(acc_emi),
            "emi_latest_duedate": acc_due,
            "is_overdue": acc_overdue,
            "outstanding": r2(acc_outstanding),
        })

    return {
        "delinquency": {
            "cnt_delinquent_c30": min(overdue_count, total_loans),
            "cnt_delinquent_c60": min(overdue_count, total_loans),
            "cnt_overdue_senders_c60": min(overdue_count, total_loans),
        },
        "approvals": {
            "cnt_approved_c30": approved,
            "cnt_rejected_c30": rejected,
        },
        "primary_loan_emi": primary_emi,
        "total_accounts": total_loans,
        "accounts": accounts,
    }
