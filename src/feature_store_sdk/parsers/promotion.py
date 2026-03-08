"""
promotion.py
------------
Promotion SMS parser for the feature_store_sdk.
"""

import re

from ..models import PromotionParsed


def extract_limit(text):
    if not isinstance(text, str):
        return None
    pattern = r"(?i)(?:limit|up to|upto|approved|sanctioned|loan|cash|rs\.?|inr)\s*(?:of\s*)?(?:rs\.?|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)"
    m = re.search(pattern, text)
    if not m:
        return None

    amt = m.group(1).replace(",", "")
    try:
        return float(amt)
    except Exception:
        return None


def parse_promotion_model(body, address, base_fields=None):
    """
    Parse a promotional SMS into a PromotionParsed dataclass instance.

    Parameters
    ----------
    body : str
        The SMS body text.
    address : str
        The sender address.
    base_fields : dict, optional
        Pre-computed SMSBase fields to pass through to the dataclass.

    Returns
    -------
    PromotionParsed
    """
    if not isinstance(body, str):
        body = ""
    t = body.lower()

    # --- promo_type ---
    re_cc = re.compile(r"(?i)credit\s*card|cc\b")
    re_loan = re.compile(r"(?i)\b(loan|lending|nbfc|credit\s*line|personal\s*loan)\b")
    re_cashback = re.compile(r"(?i)\bcashback\b")
    re_discount = re.compile(r"(?i)\b(discount|offer)\b")

    if re_cc.search(body):
        promo_type = "Credit Card Offer"
    elif re_loan.search(body):
        promo_type = "Loan Offer"
    elif re_cashback.search(body):
        promo_type = "Cashback"
    elif re_discount.search(body):
        promo_type = "Discount"
    else:
        promo_type = None

    # --- offered_product ---
    product_patterns = [
        (r"(?i)\bcredit\s*card\b", "Credit Card"),
        (r"(?i)\bpersonal\s*loan\b", "Personal Loan"),
        (r"(?i)\bhome\s*loan\b", "Home Loan"),
        (r"(?i)\bcar\s*loan\b", "Car Loan"),
        (r"(?i)\bgold\s*loan\b", "Gold Loan"),
        (r"(?i)\bbusiness\s*loan\b", "Business Loan"),
        (r"(?i)\bcredit\s*line\b", "Credit Line"),
        (r"(?i)\bloan\b", "Loan"),
    ]
    offered_product = None
    for pat, label in product_patterns:
        if re.search(pat, body):
            offered_product = label
            break

    # --- offered_limit (reuse existing function) ---
    offered_limit = extract_limit(body)

    # --- merchant ---
    merchant_names = [
        "Amazon", "Flipkart", "Myntra", "Swiggy", "Zomato",
        "BigBasket", "Croma", "Nykaa", "Ajio", "Meesho",
        "PhonePe", "Paytm", "Google Pay", "MakeMyTrip",
        "BookMyShow", "Uber", "Ola",
    ]
    merchant = None
    for name in merchant_names:
        if name.lower() in t:
            merchant = name
            break

    # --- has_cta ---
    has_cta = bool(re.search(r"(?i)\b(click|apply\s*now)\b|https?://|www\.", body))

    # --- has_expiry ---
    has_expiry = bool(re.search(r"(?i)(valid\s+till|expires?|offer\s+valid)", body))

    # Build kwargs, starting from base_fields if provided
    kwargs = dict(base_fields) if base_fields else {}
    kwargs.update(
        raw_body=body,
        sender_address=address,
        sms_category="Promotions",
        promo_type=promo_type,
        offered_product=offered_product,
        offered_limit=offered_limit,
        merchant=merchant,
        has_cta=has_cta,
        has_expiry=has_expiry,
    )

    return PromotionParsed(**kwargs)
