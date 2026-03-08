"""
insurance.py
------------
Insurance SMS parser for the feature_store_sdk.
"""

import re

from ..models import InsuranceParsed


def parse_insurance_model(body, address, base_fields=None):
    """Parse a single insurance SMS into an InsuranceParsed dataclass instance.

    Parameters
    ----------
    body : str
        The raw SMS body text.
    address : str
        The sender address / phone number.
    base_fields : dict, optional
        Pre-computed SMSBase fields to populate on the returned dataclass.

    Returns
    -------
    InsuranceParsed
        A dataclass instance with extracted insurance features.
    """
    msg = str(body) if body else ""

    # --- Insurer name & insurance type ---
    insurer_name = None
    insurance_type = None
    if "Niva Bupa" in msg:
        insurer_name = "Niva Bupa"
        insurance_type = "Health"
    elif "LIC" in msg:
        insurer_name = "LIC"
        insurance_type = "Life"

    # --- Event type ---
    event_type = None
    msg_lower = msg.lower()
    if "renewed" in msg_lower or "renewal" in msg_lower:
        event_type = "Renewal"
    elif "due" in msg_lower:
        event_type = "Premium Due"
    elif "active" in msg_lower:
        event_type = "New Policy"
    elif "health check-up" in msg_lower:
        event_type = "Wellness"
    elif "Survival Benefit" in msg:
        event_type = "Payout"

    # --- Policy number ---
    policy_number = None
    policy_match = re.search(r'Policy\s?No\.?\s?(\d+)', msg, re.I)
    if policy_match:
        policy_number = policy_match.group(1)

    # --- Premium amount ---
    premium_amount = None
    amt_match = re.search(r'Rs\.?\s?\**(\d+\.?\d*)', msg)
    if amt_match:
        premium_amount = float(amt_match.group(1))

    # --- Beneficiary name ---
    beneficiary_name = None
    name_match = re.search(
        r'Dear\s?(Mr\.|Ms\.)\s?([A-Za-z\s\.]+?)(?=\s(?:on|we|your|would))',
        msg,
    )
    if name_match:
        beneficiary_name = name_match.group(2).strip()

    # --- Date extraction helper ---
    date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{2,4})'

    # --- Due date ---
    due_date = None
    due_date_match = re.search(date_pattern, msg, re.I)
    if due_date_match:
        due_date = due_date_match.group(1).strip()

    # --- Renewal date (date appearing near "renewal" / "renew") ---
    renewal_date = None
    renewal_region = re.search(
        r'(?:renew(?:al|ed)?).{0,40}?' + date_pattern,
        msg,
        re.I,
    )
    if renewal_region:
        renewal_date = renewal_region.group(1).strip()

    # --- Build kwargs for the dataclass ---
    kwargs = dict(
        raw_body=msg,
        sender_address=str(address) if address else "",
        insurer_name=insurer_name,
        insurance_type=insurance_type,
        event_type=event_type,
        policy_number=policy_number,
        premium_amount=premium_amount,
        beneficiary_name=beneficiary_name,
        due_date=due_date,
        renewal_date=renewal_date,
    )

    # Overlay any pre-computed base fields
    if base_fields and isinstance(base_fields, dict):
        for key, value in base_fields.items():
            kwargs.setdefault(key, value)

    return InsuranceParsed(**kwargs)
