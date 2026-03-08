"""
lending.py
----------
Lending/loan/EMI SMS parser for the feature_store_sdk.
"""

import re

from ..models import LendingParsed
from ._helpers import _safe_amount, _safe_date


def parse_lending_model(body, address, base_fields=None):
    """Parse a lending SMS into a LendingParsed dataclass instance.

    Parameters
    ----------
    body : str
        The SMS body text.
    address : str
        The sender address.
    base_fields : dict, optional
        Pre-computed SMSBase fields.

    Returns
    -------
    LendingParsed
    """
    msg = str(body) if body else ""
    t = msg.lower()

    loan_account = None
    acc_match = re.search(r'(?:a/c|ac|account|loan)\s*(?:no\.?\s*)?[:\s]*(?:X+|[*]+)?\s*(\d{3,12})', msg, re.I)
    if acc_match:
        loan_account = acc_match.group(1)

    lender_name = base_fields.get("entity_name") if base_fields else None

    event_type = None
    if re.search(r'\b(disburs)', t):
        event_type = "Disbursement"
    elif re.search(r'\b(overdue|past\s*due)', t):
        event_type = "Overdue"
    elif re.search(r'\bemi\b.*\b(paid|debited|deducted)', t):
        event_type = "EMI Paid"
    elif re.search(r'\bemi\b.*\b(due|upcoming|reminder)', t):
        event_type = "EMI Due"
    elif re.search(r'\b(approved|sanctioned)', t):
        event_type = "Approved"
    elif re.search(r'\b(rejected|declined)', t):
        event_type = "Rejected"
    elif re.search(r'\b(limit.*(?:increased|decreased|changed))', t):
        event_type = "Limit Change"

    emi_amount = None
    emi_match = re.search(r'emi\s*(?:of|:|\s)\s*(?:Rs|INR)\.?\s*([\d,]+(?:\.\d{1,2})?)', msg, re.I)
    if emi_match:
        emi_amount = float(emi_match.group(1).replace(',', ''))

    outstanding = None
    out_match = re.search(r'(?:outstanding|balance|due)\s*(?:of|:|\s)\s*(?:Rs|INR)\.?\s*([\d,]+(?:\.\d{1,2})?)', msg, re.I)
    if out_match:
        outstanding = float(out_match.group(1).replace(',', ''))

    sanctioned_amount = _safe_amount(msg) if event_type == "Disbursement" else None
    due_date = _safe_date(msg)

    kwargs = dict(base_fields) if base_fields else {}
    kwargs.update(
        raw_body=msg,
        sender_address=str(address or ""),
        sms_category="Lending",
        loan_account=loan_account,
        lender_name=lender_name,
        event_type=event_type,
        emi_amount=emi_amount,
        outstanding=outstanding,
        sanctioned_amount=sanctioned_amount,
        due_date=due_date,
        is_overdue=bool(re.search(r'\b(overdue|past\s*due)', t)),
        is_emi=bool(re.search(r'\bemi\b', t)),
        is_disbursement=(event_type == "Disbursement"),
    )
    return LendingParsed(**kwargs)
