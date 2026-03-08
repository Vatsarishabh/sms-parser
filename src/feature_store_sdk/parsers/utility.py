"""
utility.py
----------
Utility bill SMS parser for the feature_store_sdk.
"""

import re

from ..models import UtilityBillParsed
from ._helpers import _safe_amount, _safe_date


def parse_utility_model(body, address, base_fields=None):
    """Parse a utility bill SMS into a UtilityBillParsed dataclass instance.

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
    UtilityBillParsed
    """
    msg = str(body) if body else ""
    t = msg.lower()

    bill_type = None
    for keyword, label in [
        ("electricity", "Electricity"), ("water", "Water"), ("gas", "Gas"),
        ("mobile", "Mobile"), ("broadband", "Broadband"), ("dth", "DTH"),
        ("recharge", "Recharge"),
    ]:
        if keyword in t:
            bill_type = label
            break

    provider = None
    for name in ["BSNL", "Jio", "Airtel", "Vi", "BESCOM", "MSEDCL", "Tata Power",
                  "Adani", "CESC", "Torrent", "KSEB"]:
        if name.lower() in t:
            provider = name
            break

    consumer_number = None
    cn_match = re.search(r'(?:consumer|customer|account)\s*(?:no\.?|number|id)\s*[:\s]*(\w{5,20})', msg, re.I)
    if cn_match:
        consumer_number = cn_match.group(1)

    kwargs = dict(base_fields) if base_fields else {}
    kwargs.update(
        raw_body=msg,
        sender_address=str(address or ""),
        sms_category="Utility Bills",
        bill_type=bill_type,
        provider=provider,
        consumer_number=consumer_number,
        bill_amount=_safe_amount(msg),
        due_date=_safe_date(msg),
        is_payment_confirmation=bool(re.search(r'\b(paid|successful|received|thank)', t)),
        is_due_reminder=bool(re.search(r'\b(due|reminder|pending|overdue)', t)),
    )
    return UtilityBillParsed(**kwargs)
