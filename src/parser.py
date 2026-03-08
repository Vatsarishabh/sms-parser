"""
parser.py
---------
Unified SMS parsing dispatcher.

Flow:  raw SMS → tagger (classify + tag) → parser.parse_sms() → typed data model

Usage:
    from src.parser import parse_sms, parse_sms_batch

    model = parse_sms(body="INR 2000 debited from A/C XX8263", address="VK-CANBNK-T")
    # Returns a TransactionParsed instance

    results = parse_sms_batch(df)
    # Returns list of dataclass dicts
"""

import re
import pandas as pd

from src.classifier import get_classifier, ClassificationResult
from src.tagger import identify_sender, decode_sender_meta
from src.models import (
    SMSBase, CATEGORY_MODEL_MAP, get_model_for_category,
    TransactionParsed, LendingParsed, InsuranceParsed,
    InvestmentParsed, EPFOParsed, UtilityBillParsed,
    PromotionParsed, OrderParsed, SecurityAlertParsed, OTPParsed,
)
from src.transaction import parse_transaction_model
from src.insurance import parse_insurance_model
from src.investment import parse_investment_model
from src.promotion import parse_promotion_model

# Module-level classifier — swappable via set_classifier()
_classifier = get_classifier("rules")


def set_classifier(strategy: str = "rules", **kwargs):
    """Switch the classification strategy at runtime."""
    global _classifier
    _classifier = get_classifier(strategy, **kwargs)


# ---------------------------------------------------------------------------
# Lightweight parsers for categories without dedicated modules
# ---------------------------------------------------------------------------

def _safe_amount(text):
    """Extract first currency amount from text."""
    m = re.search(r'(?:Rs|INR)\.?\s*([\d,]+(?:\.\d{1,2})?)', text, re.I)
    if m:
        return float(m.group(1).replace(',', ''))
    return None


def _safe_date(text):
    """Extract first date-like string from text."""
    m = re.search(
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{2,4})',
        text, re.I
    )
    return m.group(1).strip() if m else None


def _parse_lending(body, address, base_fields):
    msg = str(body) if body else ""
    t = msg.lower()

    loan_account = None
    acc_match = re.search(r'(?:a/c|ac|account|loan)\s*(?:no\.?\s*)?[:\s]*(?:X+|[*]+)?\s*(\d{3,12})', msg, re.I)
    if acc_match:
        loan_account = acc_match.group(1)

    lender_name = base_fields.get("bank_name") if base_fields else None

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


def _parse_epfo(body, address, base_fields):
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


def _parse_utility(body, address, base_fields):
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


def _parse_order(body, address, base_fields):
    msg = str(body) if body else ""
    t = msg.lower()

    merchant = None
    for name in ["Amazon", "Flipkart", "Myntra", "Swiggy", "Zomato", "BigBasket",
                  "Meesho", "Ajio", "Nykaa", "Croma"]:
        if name.lower() in t:
            merchant = name
            break

    order_id = None
    oid_match = re.search(r'(?:order)\s*(?:id|no\.?|#)\s*[:\s]*([A-Z0-9-]{5,25})', msg, re.I)
    if oid_match:
        order_id = oid_match.group(1)

    event_type = None
    if re.search(r'\bdeliver(?:ed|y)', t):
        event_type = "Delivered"
    elif re.search(r'\bshipped|dispatched', t):
        event_type = "Shipped"
    elif re.search(r'\bout for delivery', t):
        event_type = "Out for Delivery"
    elif re.search(r'\bplaced|confirmed', t):
        event_type = "Placed"
    elif re.search(r'\bcancelled|canceled', t):
        event_type = "Cancelled"
    elif re.search(r'\breturn', t):
        event_type = "Returned"

    delivery_partner = None
    for dp in ["Ekart", "Delhivery", "BlueDart", "DTDC", "Shadowfax", "Dunzo"]:
        if dp.lower() in t:
            delivery_partner = dp
            break

    kwargs = dict(base_fields) if base_fields else {}
    kwargs.update(
        raw_body=msg,
        sender_address=str(address or ""),
        sms_category="Orders",
        merchant=merchant,
        order_id=order_id,
        event_type=event_type,
        amount=_safe_amount(msg),
        delivery_partner=delivery_partner,
        estimated_date=_safe_date(msg),
    )
    return OrderParsed(**kwargs)


def _parse_security_alert(body, address, base_fields):
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


def _parse_otp(body, address, base_fields):
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


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_CATEGORY_PARSERS = {
    "Transactions": lambda body, addr, bf: parse_transaction_model(body, addr, bf),
    "Insurance": lambda body, addr, bf: parse_insurance_model(body, addr, bf),
    "Investments": lambda body, addr, bf: parse_investment_model(body, addr, bf),
    "Promotions": lambda body, addr, bf: parse_promotion_model(body, addr, bf),
    "Lending": _parse_lending,
    "EPFO": _parse_epfo,
    "Utility Bills": _parse_utility,
    "Orders": _parse_order,
    "Security Alert": _parse_security_alert,
    "OTP": _parse_otp,
}


def parse_sms(body, address, category=None, timestamp=None):
    """
    Unified entry point: classify + parse a single SMS into its typed data model.

    Parameters
    ----------
    body : str          - SMS text
    address : str       - Sender address (e.g. 'VK-CANBNK-T')
    category : str      - Pre-classified category (if None, will auto-classify)
    timestamp : str     - Optional timestamp string

    Returns
    -------
    SMSBase subclass instance (TransactionParsed, LendingParsed, etc.)
    """
    body = str(body) if body else ""
    address = str(address) if address else ""

    # Step 1: Classify (via pluggable strategy — rules, fasttext, or ensemble)
    result = _classifier.classify(body, address)

    # Use provided category override if given, otherwise use classifier output
    if not category:
        category = result.category

    # Step 2: Build base fields (sender metadata + classification output)
    meta = decode_sender_meta(address)
    base_fields = {
        "bank_name": meta["entity_name"],
        "header_code": meta["header_code"],
        "traffic_type": meta["traffic_type"],
        "sms_category": category,
        "occurrence_tag": result.occurrence_tag,
        "alphabetical_tag": result.alphabetical_tag,
        "tag_count": result.tag_count,
        "timestamp": timestamp,
    }

    # Step 3: Dispatch to category-specific parser
    parser_fn = _CATEGORY_PARSERS.get(category)
    if parser_fn:
        return parser_fn(body, address, base_fields)

    # Fallback: return SMSBase for unknown categories
    return SMSBase(raw_body=body, sender_address=address, **base_fields)


def parse_sms_batch(df):
    """
    Parse an entire DataFrame of SMS messages.

    Expects columns: 'body', 'address'. Optionally 'date', 'sms_category'.

    Returns
    -------
    list[dict] - One dict per row with all parsed fields.
    """
    results = []
    has_category = "sms_category" in df.columns
    has_date = "date" in df.columns

    for _, row in df.iterrows():
        body = row.get("body", "")
        address = row.get("address", "")
        category = row["sms_category"] if has_category else None
        timestamp = str(row["date"]) if has_date else None

        model = parse_sms(body, address, category=category, timestamp=timestamp)
        results.append(model.to_dict())

    return results