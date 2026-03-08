"""
security.py
-----------
Security alert SMS parser for the feature_store_sdk.
"""

import re

from ..models import SecurityAlertParsed


def parse_security_model(body, address, base_fields=None):
    """Parse a security alert SMS into a SecurityAlertParsed dataclass instance.

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
    SecurityAlertParsed
    """
    msg = str(body) if body else ""
    t = msg.lower()

    alert_type = None
    if re.search(r'\bblock.*card|card.*block', t):
        alert_type = "Card Block"
    elif re.search(r'\bblock.*upi|upi.*block', t):
        alert_type = "UPI Block"
    elif re.search(r'\bfraud|suspicious', t):
        alert_type = "Fraud Report"
    elif re.search(r'\breport', t):
        alert_type = "Suspicious Activity"

    affected = None
    af_match = re.search(r'(?:card|a/c|account)\s*(?:X+|[*]+)?\s*(\d{3,4})', msg, re.I)
    if af_match:
        affected = af_match.group(1)

    action_taken = None
    if "blocked" in t:
        action_taken = "Blocked"
    elif "reported" in t:
        action_taken = "Reported"
    elif re.search(r'under review|investigating', t):
        action_taken = "Under Review"

    kwargs = dict(base_fields) if base_fields else {}
    kwargs.update(
        raw_body=msg,
        sender_address=str(address or ""),
        sms_category="Security Alert",
        alert_type=alert_type,
        affected_instrument=affected,
        action_taken=action_taken,
    )
    return SecurityAlertParsed(**kwargs)
