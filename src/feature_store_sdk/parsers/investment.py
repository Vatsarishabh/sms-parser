"""
investment.py
-------------
Investment SMS parser for the feature_store_sdk.
"""

import re

from ..models import InvestmentParsed


# Platform detection patterns — order matters (more specific first)
_PLATFORMS = [
    (r"mmtc[\s\-]*pamp", "MMTC PAMP"),
    (r"icici\s*pru(?:dential)?", "ICICI Prudential"),
    (r"paytm\s*money", "Paytm Money"),
    (r"et\s*money", "ET Money"),
    (r"zerodha|iccl", "Zerodha"),
    (r"groww", "Groww"),
    (r"\bcams\b", "CAMS"),
    (r"\bcoin\b", "Coin"),
    (r"kuvera", "Kuvera"),
    (r"indmoney", "INDmoney"),
    (r"hdfc\s*(?:mutual\s*fund|mf|amc)", "HDFC MF"),
    (r"sbi\s*(?:mutual\s*fund|mf|amc)", "SBI MF"),
    (r"axis\s*(?:mutual\s*fund|mf|amc)", "Axis MF"),
    (r"nippon", "Nippon India MF"),
    (r"dsp\s*(?:mutual|mf)", "DSP MF"),
    (r"kotak\s*(?:mutual|mf|amc)", "Kotak MF"),
    (r"tata\s*(?:mutual|mf|amc)", "Tata MF"),
]


def _detect_platform(text):
    """Match the first known investment platform in text."""
    for pattern, name in _PLATFORMS:
        if re.search(pattern, text, re.I):
            return name
    return None


def parse_investment_model(body, address, base_fields=None):
    """Parse an investment SMS into an InvestmentParsed dataclass instance.

    Parameters
    ----------
    body : str
        The SMS body text.
    address : str
        The sender address / phone number.
    base_fields : dict, optional
        Pre-computed SMSBase fields (entity_name, header_code, traffic_type,
        occurrence_tag, alphabetical_tag, tag_count, timestamp, etc.)
        to populate on the model.

    Returns
    -------
    InvestmentParsed
    """
    msg = str(body) if body is not None else ""
    msg_upper = msg.upper()
    msg_lower = msg.lower()

    # --- asset_type ---
    asset_type = None
    if any(kw in msg_upper for kw in ("PAMP", "GOLD")):
        asset_type = "Gold"
    elif any(kw in msg_upper for kw in ("FUND", "MOMF", "IPRUMF", "MF", "ICCL", "COIN", "SCHEME", "FOLIO")):
        asset_type = "Mutual Fund"
    elif any(kw in msg_upper for kw in ("STOCK MARKET", "EQUITY", "SHARES", "NSE", "BSE")):
        asset_type = "Stock"

    # --- platform ---
    platform = _detect_platform(msg)

    # --- event_type ---
    event_type = None
    if re.search(r"requested\s+money|has\s+requested", msg_lower):
        event_type = "SIP Debit"
    elif re.search(r"allotted|subscription|subscribed", msg_lower):
        event_type = "Units Allotted"
    elif re.search(r"has\s+received|received\s+rs", msg_lower):
        event_type = "Purchase"
    elif "registration" in msg_lower:
        event_type = "Registration"
    elif re.search(r"redeem|redeemed|redemption", msg_lower):
        event_type = "Redemption"
    elif "dividend" in msg_lower:
        event_type = "Dividend"
    elif re.search(r"revised|revision|switched", msg_lower):
        event_type = "Scheme Revision"
    elif re.search(r"statement|portfolio\s+value", msg_lower):
        event_type = "Statement"

    # --- amount ---
    amount = None
    amt_match = re.search(r"Rs\.?\s?(\d[\d,]*\.?\d*)", msg)
    if amt_match:
        amount = float(amt_match.group(1).replace(",", ""))

    # --- nav ---
    nav = None
    nav_match = re.search(r"NAV\s?:?\s?(\d+\.?\d*)", msg, re.I)
    if nav_match:
        nav = float(nav_match.group(1))

    # --- units ---
    units = None
    units_match = re.search(r"(\d+\.?\d*)\s*units", msg, re.I)
    if units_match:
        units = float(units_match.group(1))

    # --- flags ---
    is_sip = bool(re.search(r"\bsip\b", msg_lower))
    is_redemption = "redeem" in msg_lower

    # --- fund_name ---
    fund_name = None
    fund_match = re.search(r"(?:scheme|fund)\s*[-:]\s*(.+?)(?:\.|,|$)", msg, re.I)
    if fund_match:
        fund_name = fund_match.group(1).strip()

    # Build keyword arguments, seeding from base_fields if provided
    kwargs = dict(base_fields) if base_fields else {}
    kwargs.update(
        raw_body=msg,
        sender_address=str(address) if address is not None else "",
        sms_category="Investments",
        asset_type=asset_type,
        fund_name=fund_name,
        platform=platform,
        event_type=event_type,
        amount=amount,
        nav=nav,
        units=units,
        is_sip=is_sip,
        is_redemption=is_redemption,
    )

    return InvestmentParsed(**kwargs)