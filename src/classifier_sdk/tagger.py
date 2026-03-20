import os
import json
import ahocorasick

KEYWORD_TAG_MAP = {
    "inr": "CUR", "rs": "CUR", "rs.": "CUR",
    "amount": "AMT_LBL", "money": "AMT_LBL", "cash": "AMT_LBL",

    "account": "ACC", "a/c": "ACC", "acct": "ACC", "no.": "ACC",
    "card": "CARD", "blkcc": "CARD_BLOCK",
    "upi": "UPI", "vpa": "UPI", "blockupi": "UPI_BLOCK",
    "loan": "LOAN", "emi": "LOAN_EMI", "freo": "LOAN_APP",

    "debited": "TXN_OUT", "spent": "TXN_OUT", "paid": "TXN_OUT", "spends": "TXN_OUT",
    "credited": "TXN_IN", "received": "TXN_IN", "cashback": "TXN_IN",
    "refund": "TXN_REV", "reversed": "TXN_REV",
    "payment": "TXN_GEN", "transaction": "TXN_GEN", "transfer": "TXN_GEN",
    "neft": "TXN_CHNL", "imps": "TXN_CHNL", "rtgs": "TXN_CHNL",
    "thru": "TXN_CHNL", "via": "TXN_CHNL",
    "debit": "TXN_OUT", "credit": "TXN_IN",
    "sent via": "TXN_OUT", "payee": "TXN_GEN", "ref no": "TXN_GEN",
    "txns": "TXN_GEN", "trf": "TXN_CHNL", "p2a": "TXN_CHNL", "p2m": "TXN_CHNL",

    "avail.bal": "BAL", "bal": "BAL", "balance": "BAL", "avl": "BAL",
    "updated": "BAL_UPDATE",
    "limit": "LIMIT", "limit:": "LIMIT", "lmt": "LIMIT", "limi": "LIMIT",
    "total": "LIMIT_TOT",

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
    "angel one": "INVEST_APP", "upstox": "INVEST_APP",
    "5paisa": "INVEST_APP", "motilal": "INVEST_APP",
    "iifl securities": "INVEST_APP", "sharekhan": "INVEST_APP",
    "smallcase": "INVEST_APP", "icici direct": "INVEST_APP",
    "fund bal": "INVEST_PORT", "securities bal": "INVEST_DEMAT",
    "pms bal": "INVEST_PORT", "dp bal": "INVEST_DEMAT",
    "nifty": "INVEST_STOCK", "sensex": "INVEST_STOCK",
    "trading": "INVEST_STOCK", "traded": "INVEST_STOCK",
    "buy order": "INVEST_STOCK", "sell order": "INVEST_STOCK",
    "market order": "INVEST_STOCK", "limit order": "INVEST_STOCK",
    "gold bond": "INVEST_MF", "sovereign gold": "INVEST_MF",

    "amazon": "MERCHANT", "flipkart": "MERCHANT", "swiggy": "MERCHANT",
    "zomato": "MERCHANT", "haldirams": "MERCHANT", "fnp": "MERCHANT",
    "myntra": "MERCHANT",
    "netflix": "SERVICE", "xstream": "SERVICE", "pvr": "SERVICE",

    "insurance": "INSURE", "niva": "INSURE", "bupa": "INSURE",
    "prudential": "INSURE",
    "policy": "INSURE_DOC", "premium": "INSURE_PAY",
    "sum assured": "INSURE_SUM", "renewal": "INSURE_RENEW",
    "insurance claim": "INSURE_ACTION", "claim status": "INSURE_ACTION",

    "repayment": "LOAN_REPAY", "overdue": "LOAN_OVERDUE",
    "due amount": "LOAN_DUE", "credit limit": "LOAN_CLIMIT",
    "disbursed": "LOAN_DISB", "interest charged": "LOAN_INT",
    "sanctioned": "LOAN_SANC",
    "member code": "LOAN", "instl.no": "LOAN_REPAY",
    "received with thanks": "LOAN_REPAY",
    "kreditbee": "LOAN_APP", "lazypay": "LOAN_APP", "zestmoney": "LOAN_APP",
    "moneytap": "LOAN_APP", "nira finance": "LOAN_APP", "nirafn": "LOAN_APP",
    "kissht": "LOAN_APP", "stashfin": "LOAN_APP", "fibe": "LOAN_APP",
    "olyv": "LOAN_APP", "smartcoin": "LOAN_APP", "axio": "LOAN_APP",
    "zype": "LOAN_APP", "privo": "LOAN_APP", "prefr": "LOAN_APP",
    "mobikwik zip": "LOAN_APP", "mobikwik": "LOAN_APP",
    "flipkart pay later": "LOAN_APP", "pay later": "LOAN_APP",
    "asirvad": "LOAN_APP", "shriram": "LOAN_APP",
    "muthoot": "LOAN_APP", "manappuram": "LOAN_APP",
    "truebalance": "LOAN_APP", "true balance": "LOAN_APP",
    "bajaj finance": "LOAN_APP", "bajaj finserv": "LOAN_APP",
    "personal loan": "LOAN", "cash loan": "LOAN", "instant loan": "LOAN",
    "home loan": "LOAN", "business loan": "LOAN", "gold loan": "LOAN",
    "credit line": "LOAN", "flexi loan": "LOAN", "flexi credit": "LOAN",
    "pre-approved loan": "LOAN_SANC", "pre approved loan": "LOAN_SANC",
    "loan offer": "LOAN", "apply for loan": "LOAN",
    "bnpl": "LOAN_APP", "buy now pay later": "LOAN_APP",

    "epfo": "EPFO", "pf contribution": "EPFO_CONTRIB",
    "uan": "EPFO_UAN", "provident fund": "EPFO_PF", "pension": "EPFO_PENSION",

    "electricity bill": "UTIL_ELEC", "water bill": "UTIL_WATER",
    "gas bill": "UTIL_GAS", "mobile bill": "UTIL_MOBILE",
    "broadband": "UTIL_NET", "recharge": "UTIL_RECHARGE",
    "bill payment": "UTIL_BILLPAY", "due date": "UTIL_DUE",
    "data quota": "UTIL_NET", "quota exhausted": "UTIL_NET",
    "high speed data": "UTIL_NET", "gb data": "UTIL_NET",
    "data used": "UTIL_NET", "data balance": "UTIL_NET",
    "data pack": "UTIL_NET", "daily data": "UTIL_NET",
    "data expired": "UTIL_NET", "internet data": "UTIL_NET",
    "4g data": "UTIL_NET", "5g data": "UTIL_NET",
    "pack expires": "UTIL_MOBILE", "pack expired": "UTIL_MOBILE",
    "pack expiry": "UTIL_MOBILE", "plan expires": "UTIL_MOBILE",
    "plan expiry": "UTIL_MOBILE", "validity expires": "UTIL_MOBILE",
    "postpaid": "UTIL_MOBILE", "prepaid": "UTIL_MOBILE",
    "dth": "UTIL_NET", "fastag": "UTIL_MOBILE",
    "bpcl": "UTIL_GAS", "ufill": "UTIL_GAS",
    "fuel": "UTIL_GAS", "petrol": "UTIL_GAS", "diesel": "UTIL_GAS",

    "reported": "SEC_ALERT",
    "fraud": "SEC_ALERT", "cyber fraud": "SEC_ALERT", "fraud alert": "SEC_ALERT",
    "suspicious": "SEC_ALERT", "blocked": "SEC_ALERT",
    "wrong": "SEC_ALERT", "locked": "SEC_ALERT",
    "pin": "SEC_CODE", "code:": "SEC_CODE", "otp": "OTP",
    "service code": "OTP", "paytm code": "OTP",
    "activation code": "OTP", "verification code": "OTP",
    "is your code": "OTP", "agent code": "OTP",
    "secure code": "OTP", "access code": "OTP",
    "one time password": "OTP", "one-time password": "OTP",
    "is your otp": "OTP", "is your password": "OTP",
    "unauthorized transaction": "SEC_ALERT", "unauthorised transaction": "SEC_ALERT",
    "upi registration": "UPI_BLOCK",
    "upi address": "TXN_GEN",
    "do not share your card": "CARD_BLOCK",
    "reported problem": "SEC_ALERT",
    "block your card": "CARD_BLOCK", "your card has been blocked": "CARD_BLOCK",

    "successfully": "STATUS_OK", "processed": "STATUS_OK",
    "initiated": "STATUS_START",
    "failed": "STATUS_FAIL", "declined": "STATUS_FAIL",
    "order": "ORDER", "booked": "ORDER",
    "delivery": "ORDER_DLV", "delivered": "ORDER_DLV",
    "shipped": "ORDER_DLV", "dispatched": "ORDER_DLV", "ekart": "ORDER_DLV",
    "due": "BILL_DUE", "statement": "BILL_DOC",
    "mandate": "MANDATE",
    "order id": "ORDER", "order placed": "ORDER",
    "order confirmed": "ORDER", "order status": "ORDER",
    "missed call": "OTHER_SIG", "share your feedback": "OTHER_SIG",
    "survey": "OTHER_SIG", "rate your experience": "OTHER_SIG",
    "voice assistant": "OTHER_SIG",

    "offer": "PROMO", "discount": "PROMO", "cashback offer": "PROMO",
    "coupon": "PROMO", "deal": "PROMO", "flat": "PROMO",
    "% off": "PROMO", "limited time": "PROMO",
    "shop now": "PROMO", "buy now": "PROMO", "grab": "PROMO",
    "earned": "PROMO", "points": "PROMO",
    "congratulations": "PROMO", "prize pool": "PROMO", "prize": "PROMO",
    "rummy": "PROMO", "rummycircle": "PROMO", "junglee": "PROMO",
    "gaming": "PROMO", "game wallet": "PROMO",
    "win big": "PROMO", "win now": "PROMO",
    "claim your": "PROMO", "claim now": "PROMO",
    "register now": "PROMO", "download now": "PROMO",
    "free gb": "PROMO", "free data": "PROMO",
    "bonus cash": "PROMO", "reward points": "PROMO",
    "scratch": "PROMO", "lucky draw": "PROMO",
    "upto rs": "PROMO", "upto inr": "PROMO",
}

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
        # Exclude real money movement — those are transactions with a security disclaimer, not alerts
        "exclude": {"TXN_OUT", "TXN_IN", "TXN_GEN"},
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
        # CC overdue/EMI = transactions, not lending (labelling guide rule 2)
        "exclude": {"CARD"},
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
                      "ACC", "UPI", "CARD", "BILL_DOC",
                      "MANDATE", "BAL_UPDATE"},
        "boost": {"CUR", "BAL", "BANK", "MERCHANT", "STATUS_OK",
                  "LIMIT", "FINTECH_APP", "LIMIT_TOT"},
        "priority": 4,
        "exclude": {"GOLD_ORG", "INVEST_APP", "INVEST_MF", "INVEST_SIP",
                     "INVEST_NAV", "INVEST_DEMAT", "INVEST_DIV", "INVEST_NFO",
                     "INVEST_STOCK", "INVEST_PORT", "INVEST_FOLIO",
                     "INVEST_ALLOT",
                     "INSURE", "INSURE_DOC", "INSURE_PAY", "INSURE_SUM",
                     "INSURE_RENEW", "INSURE_ACTION",
                     "EPFO", "EPFO_CONTRIB", "EPFO_UAN", "EPFO_PF", "EPFO_PENSION",
                     "OTHER_SIG"},
    },
}

_SENDER_MAP_PATH = os.path.join(os.path.dirname(__file__), "data", "sender_map.json")
_SENDER_MAP: dict[str, str] = {}
if os.path.exists(_SENDER_MAP_PATH):
    with open(_SENDER_MAP_PATH, "r", encoding="utf-8") as _f:
        _SENDER_MAP = json.load(_f)

_ENTITY_CATEGORY_HINTS: list[tuple[str, str]] = [
    ("insurance", "Insurance"),
    ("assurance", "Insurance"),
    ("life insurance", "Insurance"),
    ("general insurance", "Insurance"),
    ("broking", "Investments"),
    ("securities", "Investments"),
    ("mutual fund", "Investments"),
    ("asset management", "Investments"),
    ("capital limited", "Investments"),
    ("capital pvt", "Investments"),
    ("stock exchange", "Investments"),
    ("depository", "Investments"),
    ("finance", "Lending"),
    ("finserv", "Lending"),
    ("housing finance", "Lending"),
    ("nbfc", "Lending"),
    ("micro finance", "Lending"),
    ("bank", "Banking"),
    ("co-operative bank", "Banking"),
    ("co operative bank", "Banking"),
    ("payment", "Banking"),
    ("government", "EPFO"),
    ("provident fund", "EPFO"),
    ("epfo", "EPFO"),
]

TRAFFIC_TYPE_MAP = {
    "T": "TRANSACTIONAL",
    "S": "SERVICE",
    "P": "PROMOTIONAL",
    "G": "GOVERNMENT",
    "O": "OTP",
}


def _build_automaton():
    A = ahocorasick.Automaton()
    for keyword, tag in KEYWORD_TAG_MAP.items():
        A.add_word(keyword, (tag, keyword))
    A.make_automaton()
    return A


_AUTOMATON = _build_automaton()


def _clean_tags(tags):
    cleaned = []
    for i, tag in enumerate(tags):
        if i == 0 or tag != tags[i - 1]:
            cleaned.append(tag)
    return cleaned


def get_sms_tags(sms_text):
    sms_text = str(sms_text).lower().strip()
    if not sms_text:
        return {"occurrence_tag": "", "alphabetical_tag": "", "unique_tags": set(), "tag_count": 0}

    matches = list(_AUTOMATON.iter(sms_text))
    sorted_matches = sorted(matches, key=lambda x: x[0] - len(x[1][1]) + 1)

    occurrence_tags = [m[1][0] for m in sorted_matches]
    occurrence_tags = _clean_tags(occurrence_tags)

    unique_tags = set(occurrence_tags)
    return {
        "occurrence_tag": "*".join(occurrence_tags),
        "alphabetical_tag": "*".join(sorted(unique_tags)),
        "unique_tags": unique_tags,
        "tag_count": len(occurrence_tags),
    }


def classify_by_tags(unique_tags):
    if not unique_tags:
        return "Other"

    best_category = "Other"
    best_score = 0

    for category, rule in CATEGORY_RULES.items():
        required_hits = unique_tags & rule["required"]
        boost_hits = unique_tags & rule["boost"]
        weak_hits = unique_tags & rule.get("weak", set())

        if not required_hits:
            if len(weak_hits) < 2:
                continue
            required_hits = weak_hits

        exclude = rule.get("exclude", set())
        if exclude and (unique_tags & exclude):
            continue

        score = len(required_hits) * rule["priority"] + len(boost_hits) + len(weak_hits)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category


def _parse_sender_address(address):
    if not isinstance(address, str):
        return None, None
    parts = address.upper().split("-")
    if len(parts) >= 2:
        header_code = parts[1]
        traffic_char = parts[2] if len(parts) >= 3 else None
        return header_code, traffic_char
    return None, None


def identify_sender(address):
    header_code, _ = _parse_sender_address(address)
    if header_code and header_code in _SENDER_MAP:
        return _SENDER_MAP[header_code]
    return "unknown"


identify_bank = identify_sender


def infer_sender_category(entity_name):
    if not entity_name or entity_name == "unknown":
        return None
    lower = entity_name.lower()
    for keyword, category in _ENTITY_CATEGORY_HINTS:
        if keyword in lower:
            return category
    return None


def decode_sender_meta(sender_address):
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
    tag_result = get_sms_tags(text)
    return classify_by_tags(tag_result["unique_tags"])