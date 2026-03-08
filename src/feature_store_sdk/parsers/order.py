"""
order.py
--------
Order/delivery SMS parser for the feature_store_sdk.
"""

import re

from ..models import OrderParsed
from ._helpers import _safe_amount, _safe_date


def parse_order_model(body, address, base_fields=None):
    """Parse an order/delivery SMS into an OrderParsed dataclass instance.

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
    OrderParsed
    """
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
