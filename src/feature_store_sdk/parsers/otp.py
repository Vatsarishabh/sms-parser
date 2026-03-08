"""
otp.py
------
OTP SMS parser for the feature_store_sdk.
"""

import re

from ..models import OTPParsed


def parse_otp_model(body, address, base_fields=None):
    """Parse an OTP SMS into an OTPParsed dataclass instance.

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
    OTPParsed
    """
    msg = str(body) if body else ""
    t = msg.lower()

    otp_for = None
    if re.search(r'login|sign.?in', t):
        otp_for = "login"
    elif re.search(r'transact|payment|transfer', t):
        otp_for = "transaction"
    elif re.search(r'regist|sign.?up|verif', t):
        otp_for = "registration"

    validity_minutes = None
    val_match = re.search(r'valid\s*(?:for)?\s*(\d+)\s*min', msg, re.I)
    if val_match:
        validity_minutes = int(val_match.group(1))

    platform = None
    for name in ["Amazon", "Flipkart", "Google", "Paytm", "PhonePe",
                  "WhatsApp", "Swiggy", "Zomato", "CRED", "GPay"]:
        if name.lower() in t:
            platform = name
            break

    kwargs = dict(base_fields) if base_fields else {}
    kwargs.update(
        raw_body=msg,
        sender_address=str(address or ""),
        sms_category="OTP",
        otp_for=otp_for,
        validity_minutes=validity_minutes,
        platform=platform,
    )
    return OTPParsed(**kwargs)
