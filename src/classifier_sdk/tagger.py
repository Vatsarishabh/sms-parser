import os
import json
import ahocorasick

# 1. Keyword-to-Tag mapping for Aho-Corasick automaton
KEYWORD_TAG_MAP = {
    # --- CURRENCY & AMOUNTS ---
    "inr": "CUR", "rs": "CUR", "rs.": "CUR",
    "amount": "AMT_LBL", "money": "AMT_LBL", "cash": "AMT_LBL",

    # --- FINANCIAL INSTRUMENTS ---
    "account": "ACC", "a/c": "ACC", "acct": "ACC", "no.": "ACC",
    "card": "CARD", "blkcc": "CARD_BLOCK",
    "upi": "UPI", "vpa": "UPI", "blockupi": "UPI_BLOCK",
    "loan": "LOAN", "emi": "LOAN_EMI", "freo": "LOAN_APP",

    # --- TRANSACTION ACTIONS ---
    "debited": "TXN_OUT", "spent": "TXN_OUT", "paid": "TXN_OUT", "spends": "TXN_OUT",
    "credited": "TXN_IN", "received": "TXN_IN", "cashback": "TXN_IN",
    "refund": "TXN_REV", "reversed": "TXN_REV",
    "payment": "TXN_GEN", "transaction": "TXN_GEN", "transfer": "TXN_GEN",
    "neft": "TXN_CHNL", "imps": "TXN_CHNL", "rtgs": "TXN_CHNL",
    "thru": "TXN_CHNL", "via": "TXN_CHNL",

    # --- BALANCE & LIMITS ---
    "avail.bal": "BAL", "bal": "BAL", "balance": "BAL", "avl": "BAL",
    "updated": "BAL_UPDATE",
    "limit": "LIMIT", "limit:": "LIMIT", "lmt": "LIMIT", "limi": "LIMIT",
    "total": "LIMIT_TOT",

    # --- ENTITIES (BANKS & APPS) ---
    "canara": "BANK", "icici": "BANK", "hdfc": "BANK", "axis": "BANK",
    "sbi": "BANK", "kotak": "BANK", "bank": "BANK",
    "mmtc": "GOLD_ORG", "pamp": "GOLD_ORG",
    "zerodha": "INVEST_APP", "groww": "INVEST_APP", "securities": "INVEST_APP",
    "kuvera": "INVEST_APP", "indmoney": "INVEST_APP", "et money": "INVEST_APP",
    "paytm money": "INVEST_APP", "coin": "INVEST_APP",
    "iccl": "INVEST_APP", "indianclearingcorporation": "INVEST_APP",
    "mutual fund": "INVEST_MF", "sip": "INVEST_SIP",
    "nav:": "INVEST_NAV", "nav value": "INVEST_NAV",
    "demat": "INVEST_DEMAT", "dividend": "INVEST_DIV",
    "new fund offer": "INVEST_NFO",
    "stock market": "INVEST_STOCK", "equity": "INVEST_STOCK",
    "stocks": "INVEST_STOCK", "shares": "INVEST_STOCK",
    "portfolio": "INVEST_PORT",
    "folio": "INVEST_FOLIO", "units allotted": "INVEST_ALLOT",
    "cred": "FINTECH_APP", "paytm": "FINTECH_APP",

    # --- SHOPPING & SERVICES ---
    "amazon": "MERCHANT", "flipkart": "MERCHANT", "swiggy": "MERCHANT",
    "zomato": "MERCHANT", "haldirams": "MERCHANT", "fnp": "MERCHANT",
    "myntra": "MERCHANT",
    "netflix": "SERVICE", "xstream": "SERVICE", "pvr": "SERVICE",

    # --- INSURANCE ---
    "insurance": "INSURE", "niva": "INSURE", "bupa": "INSURE",
    "prudential": "INSURE",
    "policy": "INSURE_DOC", "premium": "INSURE_PAY",
    "sum assured": "INSURE_SUM", "renewal": "INSURE_RENEW",
    "insurance claim": "INSURE_ACTION", "claim status": "INSURE_ACTION",

    # --- LENDING ---
    "repayment": "LOAN_REPAY", "overdue": "LOAN_OVERDUE",
    "due amount": "LOAN_DUE", "credit limit": "LOAN_CLIMIT",
    "disbursed": "LOAN_DISB", "interest charged": "LOAN_INT",
    "sanctioned": "LOAN_SANC",

    # --- EPFO ---
    "epfo": "EPFO", "pf contribution": "EPFO_CONTRIB",
    "uan": "EPFO_UAN", "provident fund": "EPFO_PF", "pension": "EPFO_PENSION",

    # --- UTILITY BILLS ---
    "electricity bill": "UTIL_ELEC", "water bill": "UTIL_WATER",
    "gas bill": "UTIL_GAS", "mobile bill": "UTIL_MOBILE",
    "broadband": "UTIL_NET", "recharge": "UTIL_RECHARGE",
    "bill payment": "UTIL_BILLPAY", "due date": "UTIL_DUE",

    # --- ALERTS & SECURITY ---
    "report": "SEC_ALERT", "reported": "SEC_ALERT",
    "cyber": "SEC_ALERT", "fraud": "SEC_ALERT",
    "suspicious": "SEC_ALERT", "blocked": "SEC_ALERT",
    "wrong": "SEC_ALERT", "locked": "SEC_ALERT",
    "pin": "SEC_CODE", "code:": "SEC_CODE", "otp": "OTP",

    # --- STATUS & LOGISTICS ---
    "successfully": "STATUS_OK", "processed": "STATUS_OK",
    "initiated": "STATUS_START",
    "failed": "STATUS_FAIL", "declined": "STATUS_FAIL",
    "order": "ORDER", "booked": "ORDER",
    "delivery": "ORDER_DLV", "delivered": "ORDER_DLV",
    "shipped": "ORDER_DLV", "dispatched": "ORDER_DLV", "ekart": "ORDER_DLV",
    "due": "BILL_DUE", "statement": "BILL_DOC",
    "mandate": "MANDATE",

    # --- PROMOTIONS ---
    "offer": "PROMO", "discount": "PROMO", "cashback offer": "PROMO",
    "coupon": "PROMO", "deal": "PROMO", "flat": "PROMO",
    "% off": "PROMO", "limited time": "PROMO",
    "shop now": "PROMO", "buy now": "PROMO", "grab": "PROMO",
    "earned": "PROMO", "points": "PROMO",
}

# 2. Tag-to-Category classification rules (priority ordered)
# Each category has required tags (ANY match) and boost tags (increase confidence)
CATEGORY_RULES = {
    "OTP": {
        "required": {"OTP", "SEC_CODE"},
        "boost": set(),
        "priority": 10,
    },
    "Security Alert": {
        "required": {"SEC_ALERT", "CARD_BLOCK", "UPI_BLOCK"},
        "boost": {"CARD", "ACC", "BANK"},
        "priority": 9,
    },
    "EPFO": {
        "required": {"EPFO", "EPFO_CONTRIB", "EPFO_UAN", "EPFO_PF", "EPFO_PENSION"},
        "boost": set(),
        "priority": 8,
    },
    "Insurance": {
        "required": {"INSURE", "INSURE_DOC", "INSURE_PAY", "INSURE_SUM",
                      "INSURE_RENEW", "INSURE_ACTION"},
        "boost": {"CUR", "AMT_LBL"},
        "priority": 7,
        "exclude": {"PROMO"},
    },
    "Lending": {
        "required": {"LOAN", "LOAN_EMI", "LOAN_APP", "LOAN_REPAY", "LOAN_OVERDUE",
                      "LOAN_DUE", "LOAN_CLIMIT", "LOAN_DISB", "LOAN_INT", "LOAN_SANC"},
        "boost": {"CUR", "AMT_LBL", "BANK"},
        "priority": 6,
    },
    "Investments": {
        "required": {"INVEST_APP", "INVEST_MF", "INVEST_SIP",
                      "INVEST_DEMAT", "INVEST_DIV", "INVEST_NFO",
                      "INVEST_FOLIO", "INVEST_ALLOT",
                      "GOLD_ORG"},
        "weak": {"INVEST_NAV", "INVEST_STOCK", "INVEST_PORT"},
        "boost": {"CUR", "AMT_LBL"},
        "priority": 5,
    },
    "Utility Bills": {
        "required": {"UTIL_ELEC", "UTIL_WATER", "UTIL_GAS", "UTIL_MOBILE",
                      "UTIL_NET", "UTIL_RECHARGE", "UTIL_BILLPAY", "UTIL_DUE"},
        "boost": {"CUR", "BILL_DUE", "TXN_GEN"},
        "priority": 5,
    },
    "Orders": {
        "required": {"ORDER", "ORDER_DLV"},
        "boost": {"MERCHANT", "STATUS_OK"},
        "priority": 5,
    },
    "Promotions": {
        "required": {"PROMO"},
        "boost": {"MERCHANT", "SERVICE", "CUR"},
        "priority": 5,
    },
    "Transactions": {
        "required": {"TXN_OUT", "TXN_IN", "TXN_REV", "TXN_GEN", "TXN_CHNL",
                      "ACC", "UPI", "CARD", "BILL_DOC"},
        "boost": {"CUR", "BAL", "BANK", "MERCHANT", "STATUS_OK"},
        "priority": 4,
        "exclude": {"GOLD_ORG", "INVEST_APP", "INVEST_MF", "INVEST_SIP",
                     "INVEST_NAV", "INVEST_DEMAT", "INVEST_DIV", "INVEST_NFO",
                     "INVEST_STOCK", "INVEST_PORT", "INVEST_FOLIO",
                     "INVEST_ALLOT",
                     "INSURE", "INSURE_DOC", "INSURE_PAY", "INSURE_SUM",
                     "INSURE_RENEW", "INSURE_ACTION",
                     "EPFO", "EPFO_CONTRIB", "EPFO_UAN", "EPFO_PF", "EPFO_PENSION"},
    },
}

# 3. Sender header map — loaded from TRAI header-code → entity-name JSON
_SENDER_MAP_PATH = os.path.join(os.path.dirname(__file__), "data", "sender_map.json")
_SENDER_MAP: dict[str, str] = {}
if os.path.exists(_SENDER_MAP_PATH):
    with open(_SENDER_MAP_PATH, "r", encoding="utf-8") as _f:
        _SENDER_MAP = json.load(_f)

# 4. Entity-name keywords → category hint (used as a pre-classification signal)
_ENTITY_CATEGORY_HINTS: list[tuple[str, str]] = [
    # Insurance
    ("insurance", "Insurance"),
    ("assurance", "Insurance"),
    ("life insurance", "Insurance"),
    ("general insurance", "Insurance"),
    # Investments
    ("broking", "Investments"),
    ("securities", "Investments"),
    ("mutual fund", "Investments"),
    ("asset management", "Investments"),
    ("capital limited", "Investments"),
    ("capital pvt", "Investments"),
    ("stock exchange", "Investments"),
    ("depository", "Investments"),
    # Lending / NBFC
    ("finance", "Lending"),
    ("finserv", "Lending"),
    ("housing finance", "Lending"),
    ("nbfc", "Lending"),
    ("micro finance", "Lending"),
    # Banking
    ("bank", "Banking"),
    ("co-operative bank", "Banking"),
    ("co operative bank", "Banking"),
    ("payment", "Banking"),
    # Government / EPFO
    ("government", "EPFO"),
    ("provident fund", "EPFO"),
    ("epfo", "EPFO"),
]

# TRAI sender suffix mapping
TRAFFIC_TYPE_MAP = {
    "T": "TRANSACTIONAL",
    "S": "SERVICE",
    "P": "PROMOTIONAL",
    "G": "GOVERNMENT",
    "O": "OTP",
}


def _build_automaton():
    """Builds the Aho-Corasick automaton from the keyword-tag map (one-time cost)."""
    A = ahocorasick.Automaton()
    for keyword, tag in KEYWORD_TAG_MAP.items():
        A.add_word(keyword, (tag, keyword))
    A.make_automaton()
    return A


# Module-level singleton automaton
_AUTOMATON = _build_automaton()


def _clean_tags(tags):
    """Remove consecutive duplicate tags."""
    cleaned = []
    for i, tag in enumerate(tags):
        if i == 0 or tag != tags[i - 1]:
            cleaned.append(tag)
    return cleaned


def get_sms_tags(sms_text):
    """
    Runs Aho-Corasick on SMS text and returns structural + semantic signatures.

    Returns:
        dict with occurrence_tag, alphabetical_tag, unique_tags (set), tag_count
    """
    sms_text = str(sms_text).lower().strip()
    if not sms_text:
        return {"occurrence_tag": "", "alphabetical_tag": "", "unique_tags": set(), "tag_count": 0}

    matches = list(_AUTOMATON.iter(sms_text))
    sorted_matches = sorted(matches, key=lambda x: x[0] - len(x[1][1]) + 1)

    occurrence_tags = [m[1][0] for m in sorted_matches]
    occurrence_tags = _clean_tags(occurrence_tags)

    unique_tags = set(occurrence_tags)
    occurrence_sig = "*".join(occurrence_tags)
    alphabetical_sig = "*".join(sorted(unique_tags))

    return {
        "occurrence_tag": occurrence_sig,
        "alphabetical_tag": alphabetical_sig,
        "unique_tags": unique_tags,
        "tag_count": len(occurrence_tags),
    }


def classify_by_tags(unique_tags):
    """
    Classifies SMS category from its unique tag set using priority-scored rules.

    Returns the best matching category string.
    """
    if not unique_tags:
        return "Other"

    best_category = "Other"
    best_score = 0

    for category, rule in CATEGORY_RULES.items():
        required_hits = unique_tags & rule["required"]
        boost_hits = unique_tags & rule["boost"]
        weak_hits = unique_tags & rule.get("weak", set())

        # Need at least one strong required tag, OR 2+ weak tags
        if not required_hits:
            if len(weak_hits) < 2:
                continue
            # 2+ weak tags qualify — treat them as required hits
            required_hits = weak_hits

        # If any exclude tag is present, skip this category
        exclude = rule.get("exclude", set())
        if exclude and (unique_tags & exclude):
            continue

        # Score = (required matches * priority) + boost matches + weak matches
        score = len(required_hits) * rule["priority"] + len(boost_hits) + len(weak_hits)

        if score > best_score:
            best_score = score
            best_category = category

    return best_category


def _parse_sender_address(address):
    """Parse TRAI sender address into (header_code, traffic_type_char).

    Handles both ``XX-YYYY-Z`` and ``XX-YYYY`` (no traffic type) formats.
    Returns (None, None) for unparseable addresses.
    """
    if not isinstance(address, str):
        return None, None
    parts = address.upper().split("-")
    if len(parts) >= 2:
        header_code = parts[1]
        traffic_char = parts[2] if len(parts) >= 3 else None
        return header_code, traffic_char
    return None, None


def identify_sender(address):
    """Identify the entity name from the sender address header code.

    Looks up the TRAI header code (YYYY portion of XX-YYYY-Z or XX-YYYY)
    in the sender map JSON. Falls back to ``"Unknown"`` if not found.
    """
    header_code, _ = _parse_sender_address(address)
    if header_code and header_code in _SENDER_MAP:
        return _SENDER_MAP[header_code]
    return "unknown"


# Backward-compatible alias
identify_bank = identify_sender


def infer_sender_category(entity_name):
    """Derive a category hint from the entity name.

    Returns a category string (e.g. ``"Insurance"``, ``"Investments"``)
    or ``None`` if no hint can be inferred.
    """
    if not entity_name or entity_name == "unknown":
        return None
    lower = entity_name.lower()
    for keyword, category in _ENTITY_CATEGORY_HINTS:
        if keyword in lower:
            return category
    return None


def decode_sender_meta(sender_address):
    """
    Decodes a TRAI-compliant sender address into metadata.

    Handles both ``XX-YYYY-Z`` (with traffic type) and ``XX-YYYY`` (without).

    Returns:
        dict with header_code, traffic_type, entity_name, sender_category_hint
    """
    header_code, traffic_char = _parse_sender_address(sender_address)

    traffic_type = "GENERAL"
    if traffic_char:
        traffic_type = TRAFFIC_TYPE_MAP.get(traffic_char, "OTHER")

    entity_name = _SENDER_MAP.get(header_code, "unknown") if header_code else "unknown"
    sender_category_hint = infer_sender_category(entity_name)

    return {
        "header_code": header_code,
        "traffic_type": traffic_type,
        "entity_name": entity_name,
        "sender_category_hint": sender_category_hint,
    }


def tag_message(text):
    """
    Full classification pipeline for a single SMS body.
    Returns category string.
    """
    tag_result = get_sms_tags(text)
    return classify_by_tags(tag_result["unique_tags"])
