"""
epfo.py
-------
EPFO/PF SMS parser for the feature_store_sdk.
"""

import re

from ..models import EPFOParsed
from ._helpers import _safe_amount


def parse_epfo_model(body, address, base_fields=None):
    """Parse an EPFO SMS into an EPFOParsed dataclass instance.

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
    EPFOParsed
    """
    msg = str(body) if body else ""
    t = msg.lower()

    uan = None
    uan_match = re.search(r'UAN\s*[:\s]*(\d{12})', msg, re.I)
    if uan_match:
        uan = uan_match.group(1)

    event_type = None
    if "contribution" in t:
        event_type = "Contribution"
    elif re.search(r'withdraw|claim', t):
        event_type = "Withdrawal"
    elif "passbook" in t:
        event_type = "Passbook Update"
    elif "kyc" in t:
        event_type = "KYC"

    employee_share = None
    emp_match = re.search(r'employee\s*(?:share)?\s*(?:Rs|INR)\.?\s*([\d,]+(?:\.\d{1,2})?)', msg, re.I)
    if emp_match:
        employee_share = float(emp_match.group(1).replace(',', ''))

    employer_share = None
    empr_match = re.search(r'employer\s*(?:share)?\s*(?:Rs|INR)\.?\s*([\d,]+(?:\.\d{1,2})?)', msg, re.I)
    if empr_match:
        employer_share = float(empr_match.group(1).replace(',', ''))

    total_balance = _safe_amount(msg)

    contribution_month = None
    month_match = re.search(r'(?:for|month)\s*(?:of\s*)?((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\'-]*\d{2,4})', msg, re.I)
    if month_match:
        contribution_month = month_match.group(1).strip()

    kwargs = dict(base_fields) if base_fields else {}
    kwargs.update(
        raw_body=msg,
        sender_address=str(address or ""),
        sms_category="EPFO",
        uan=uan,
        event_type=event_type,
        employee_share=employee_share,
        employer_share=employer_share,
        total_balance=total_balance,
        contribution_month=contribution_month,
    )
    return EPFOParsed(**kwargs)
