import re
import pandas as pd

# -----------------------------
# 1) Cleaner (small upgrades)
# -----------------------------
def clean_text(text):
    if not isinstance(text, str) or pd.isna(text):
        return ""
    text = re.sub(r'https?://\S+', ' ', text)                 # remove URLs
    text = re.sub(r'\s+', ' ', text).strip()                  # normalize spaces

    # common formatting fixes
    text = re.sub(r"\bUPI/", "UPI ", text)
    text = re.sub(r"(\d+)(credited|debited)", r"\1 \2", text, flags=re.I)
    text = re.sub(r"(XX\d+)(via)", r"\1 \2", text, flags=re.I)
    text = re.sub(r"(\d+\.\d+)([A-Z]+)", r"\1 \2", text)
    text = re.sub(r'\bBal:\b', r'Bal: ', text, flags=re.I)
    text = re.sub(r'\bRef:\b', r'Ref: ', text, flags=re.I)
    text = re.sub(r'\bno(\d+)\b', r'no \1', text, flags=re.I)

    # remove time like 12:34:56
    text = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', ' ', text)

    return re.sub(r'\s+', ' ', text).strip()


def first_group(pattern, text, flags=re.I):
    m = re.search(pattern, text, flags)
    if not m:
        return None
    return m.group(1) if m.lastindex else m.group(0)


# -----------------------------
# 2) NEW: Offer/Marketing guard
# -----------------------------
_OFFER_PATTERNS = [
    r"\bpre[-\s]?qualified\b",
    r"\bpre[-\s]?approved\b",
    r"\bapproved\s+for\b",
    r"\byou('?re| are)\s+eligible\b",
    r"\bapply\s+now\b",
    r"\binstant\s+approval\b",
    r"\bclick\s+(now|here)\b",
    r"\boffer\b",
    r"\boffer\s+valid\b",
    r"\bvalid\s+till\b",
    r"\bzero\s+joining\s+fee\b",
    r"\bjoining\s+fee\b",
    r"\bannual\s+fee\b",
    r"\bannual\s+cashback\b",
    r"\bcashback\b",
    r"\bcredit\s+limit\b",
    r"\blimit\s+of\s+up\s+to\b",
    r"\bcard\b.*\b(offer|eligible|pre[-\s]?approved|pre[-\s]?qualified|apply)\b",
]

# If these appear, it becomes *very likely* it's NOT a transaction
_NON_TXN_STRONG_CTA = [
    r"\bhttp\b", r"\bwww\b", r"\bclick\b", r"\bapply\b", r"\bavail\b", r"\boffer\s+valid\b"
]

def is_offer_or_marketing(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    t = text.lower()

    # must NOT be an actual txn indicator
    txn_verbs = re.search(r"\b(credited|debited|spent|paid|purchase|withdrawn|received|transferred)\b", t)
    if txn_verbs:
        # still allow offers that contain "credited" as cashback marketing etc
        # but generally if txn verbs exist, don't auto-block unless strong offer cues exist
        strong_offer = any(re.search(p, t) for p in _OFFER_PATTERNS)
        strong_cta = any(re.search(p, t) for p in _NON_TXN_STRONG_CTA)
        return bool(strong_offer and strong_cta)

    # no txn verbs -> if offer markers appear, block parsing
    return any(re.search(p, t) for p in _OFFER_PATTERNS)


# -----------------------------
# 3) Reference extraction (keep yours)
# -----------------------------
def extract_reference(text):
    m = re.search(r"([A-Z]{3,6}\d{11}|\b\d{10,12}\b|Ref[:\s-]*(\d+)|UTR[:\s-]*(\d+))", text, re.I)
    if not m:
        return None
    g = m.groups()
    ref = next((x for x in g if x is not None), m.group(0))
    ref = re.sub(r'(Ref|UTR)[:\s-]*', '', ref, flags=re.I).strip()
    return ref or None


# -----------------------------
# 4) NEW: Amount extraction that avoids "limit/cashback/fees"
# -----------------------------
def extract_txn_amount(text: str):
    """
    Extract amount only when it's tied to a real transaction verb.
    Avoid credit limit, cashback, fee marketing amounts.
    """
    if not isinstance(text, str) or not text.strip():
        return None

    t = text

    # if marketing/offer, do not treat any amount as txn amount
    if is_offer_or_marketing(t):
        return None

    # Amount needs a txn verb nearby (credited/debited/paid/spent/received/withdrawn/transferred)
    # Examples:
    # "Rs 1,234 credited", "debited by INR 500", "paid Rs. 99", "spent INR 250"
    amount_patterns = [
        r"(?:rs|inr)\.?\s*([\d,]+(?:\.\d{1,2})?)\s*(?:is\s+)?(?:credited|debited|paid|spent|received|withdrawn|transferred)\b",
        r"(?:credited|debited|paid|spent|received|withdrawn|transferred)\s*(?:by\s*)?(?:rs|inr)\.?\s*([\d,]+(?:\.\d{1,2})?)\b",
        r"\bamt\b[\s:.-]*(?:rs|inr)?\.?\s*([\d,]+(?:\.\d{1,2})?)\b.*?\b(credited|debited|paid|spent|received|withdrawn|transferred)\b",
    ]

    for p in amount_patterns:
        m = re.search(p, t, re.I)
        if m:
            val = m.group(1).replace(",", "")
            return val
    return None


def extract_balance(text: str):
    if not isinstance(text, str) or not text.strip():
        return None

    # Balance/limit can appear for card offers; but balance extraction is still ok only if txn-like
    # If offer, ignore balance too.
    if is_offer_or_marketing(text):
        return None

    p_balance = r"(?:balance|bal|avl|avail\.bal|avail\s+bal|avl\s+bal)[\s\.:]*(?:rs|inr)?\.?\s*([\d,]+(?:\.\d{1,2})?)"
    b = first_group(p_balance, text)
    return b.replace(",", "") if b else None


# -----------------------------
# 5) Your payer/payee + subtype functions can remain
# (keeping minimal changes)
# -----------------------------
def extract_payer_payee(text):
    payer, payee = None, None

    m = re.search(r"UPI/[A-Z0-9]+/(\d+|[A-Z0-9]+)/([A-Z0-9\s*]{3,})", text, re.I)
    if m:
        payee = m.group(2).strip()

    if not payee:
        m = re.search(
            r"(?:to|at|towards|paid\s+to|spent\s+on)\s+([A-Z0-9\s*&]{3,25})"
            r"(?:\s+on|\s+via|\s+Ref|\.|\n|$)",
            text, re.I
        )
        if m:
            payee = m.group(1).strip()
            payee = re.sub(r"\b(on|via|Ref|RefNo|UPI|account|balance)\b.*", "", payee, flags=re.I).strip()

    m = re.search(
        r"(?:from|by|received\s+from)\s+([A-Z0-9\s*&]{3,25})"
        r"(?:\s+on|\s+via|\s+Ref|\.|\n|$)",
        text, re.I
    )
    if m:
        payer = m.group(1).strip()
        payer = re.sub(r"\b(on|via|Ref|RefNo|UPI|account|balance)\b.*", "", payer, flags=re.I).strip()

    return payer, payee


def is_salary_credit(text, txn_type):
    if txn_type != "Credit":
        return False
    if not isinstance(text, str):
        return False
    t = text.lower()
    salary_patterns = [
        r"\bsalary\b", r"\bpayroll\b", r"\bstipend\b", r"\bwages\b",
        r"\bmonthly\s+pay\b", r"\bsal\b", r"\bsal\.\b", r"\bsal\s+cr\b", r"\bpay\s+credit\b",
    ]
    return any(re.search(p, t) for p in salary_patterns)


def get_transaction_subtype(text, txn_type, mandate_flag, channel, product):
    t = text.lower()

    if is_salary_credit(text, txn_type):
        return "Salary Credit"

    if re.search(r"\b(refund|reversal|reversed|chargeback|credited\s+back)\b", t):
        return "Refund/Reversal"

    if re.search(r"\b(emi|loan\s+repay|repayment|installment|instalment)\b", t):
        return "EMI/Loan"

    if mandate_flag:
        if re.search(r"\b(failed|declined|unsuccessful|rejected|bounce)\b", t):
            return "Mandate Failed"
        if re.search(r"\b(set\s*up|setup|registered|created|activated|initiation)\b", t):
            return "Mandate Setup"
        return "Mandate Auto"

    if re.search(r"\b(bill|recharge|dth|electricity|utility|broadband|gas|water)\b", t):
        return "Bill Payment"

    if re.search(r"\batm\b", t) and re.search(r"\b(withdrawn|cash)\b", t):
        return "ATM Cash Withdrawal"

    if channel == "Card" and re.search(r"\b(purchase|pos|spent|swipe|merchant)\b", t):
        return "Card Purchase"

    if channel == "UPI":
        return "UPI Transfer"

    if channel in ["NEFT", "IMPS", "Net Banking"]:
        return "Bank Transfer"

    if product == "Credit Card":
        return "Card Transaction"
    return "General"


# -----------------------------
# 6) UPDATED parse_transaction with early marketing exit
# -----------------------------
def parse_transaction(body, address):
    t = clean_text(body)

    # EARLY EXIT: Offer/Marketing (pre-qualified card, limits, cashback, fees, CTA)
    if is_offer_or_marketing(t):
        return {
            "SenderID": address,
            "Financial Product": "Credit Card",
            "Transaction Type": "Non-Transaction",
            "Transaction Subtype": "Card Offer/Marketing",
            "Amount": None,
            "Balance": None,
            "Payee": None,
            "Reference Number": None,
            "Card Number": None,
            "Account Number": None,
            "Transaction Channel": "Generic",
            "Context": "Offer/Marketing",
            "Mandate Flag": False,
        }

    # account/card snippets (kept from your version)
    p_acc   = r"(?:a/c|ac|acc|no|card|wallet|X+|[\*]+)\s*(\d{3,4})\b"
    p_card4 = r"(?:card|ending\s+with)\s*(?:X+|[\*]+)?\s*(\d{4})\b"

    acc   = first_group(p_acc, t)
    card4 = first_group(p_card4, t)

    amount  = extract_txn_amount(t)
    balance = extract_balance(t)

    card_number = card4 if card4 else (acc if ("card" in t.lower()) else None)
    ref = extract_reference(t)

    mandate_flag = bool(re.search(r"\b(mandate|standing\s+instruction|autopay|si)\b", t, re.I))

    # Transaction Type (unchanged logic)
    if re.search(r"\b(mandate\s+alert|standing\s+instruction\s+alert)\b", t, re.I):
        txn_type = "Mandate Alert"
    elif re.search(r"\b(mandate\s+initiation|set\s+up\s+mandate|mandate\s+set)\b", t, re.I):
        txn_type = "Mandate"
    elif re.search(r"\b(credited|credit|received|deposited|reversed|reversal)\b", t, re.I):
        txn_type = "Credit"
    elif re.search(r"\b(debited|debit|sent|spent|used|paid|payment\s+of|purchase\s+at)\b", t, re.I):
        txn_type = "Debit"
    else:
        txn_type = "Unknown"

    # Channel
    if re.search(r"\bUPI\b", t, re.I):
        channel = "UPI"
    elif re.search(r"\bneft\b", t, re.I):
        channel = "NEFT"
    elif re.search(r"\bimps\b", t, re.I):
        channel = "IMPS"
    elif re.search(r"\b(card|visa|mastercard|cc|dc|credit\s+card|debit\s+card|XX\d{4})\b", t, re.I):
        channel = "Card"
    elif re.search(r"\b(wallet|rupee|eINR|postpaid|paytm\s+add\s+money|amazon\s+pay|phonepe\s+wallet)\b", t, re.I):
        channel = "Wallet"
    elif re.search(r"\b(neft|imps|rtgs)\b", t, re.I):
        channel = "Net Banking"
    else:
        channel = "Generic"

    # Financial product
    if re.search(r"\b(loan|emi)\b", t, re.I):
        product = "Loans"
    elif re.search(r"\b(wallet|rupee|eINR|postpaid|paytm\s+add\s+money|amazon\s+pay|phonepe\s+wallet)\b", t, re.I) or "wallet" in t.lower():
        product = "Wallet"
    elif re.search(r"\b(card|visa|mastercard|cc|dc|credit\s+card|debit\s+card|XX\d{4})\b", t, re.I) or "card" in t.lower():
        product = "Credit Card"
    else:
        product = "Bank Account"

    # Context
    if re.search(r"\b(refund|reversal|credited\s+back)\b", t, re.I):
        context = "Refund/Reversal"
    elif re.search(r"\b(bill|recharge|dth|electricity|utility)\b", t, re.I):
        context = "Bill Payment"
    elif mandate_flag:
        context = "Mandate Activity"
    elif product == "Credit Card":
        context = "Credit Card Transaction"
    else:
        context = "General Transaction"

    subtype = get_transaction_subtype(t, txn_type, mandate_flag, channel, product)
    payer, payee = extract_payer_payee(t)

    return {
        "SenderID": address,
        "Financial Product": product,
        "Transaction Type": txn_type,
        "Transaction Subtype": subtype,
        "Amount": amount,
        "Balance": balance,
        "Payee": payee,
        "Reference Number": ref,
        "Card Number": card_number,
        "Account Number": acc,
        "Transaction Channel": channel,
        "Context": context,
        "Mandate Flag": mandate_flag,
    }
def analyze_transactions(df):
    df = df.copy()

    required = {"body", "address", "sms_category"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    trans_df = df[df["sms_category"] == "Transactions"].copy()
    print(f"Found {len(trans_df)} transaction messages.")

    if trans_df.empty:
        cols = [
            "_id","date","SenderID","Financial Product","Transaction Type","Transaction Subtype",
            "Amount","Balance","Payee","Reference Number","Card Number","Account Number",
            "Transaction Channel","Context","Mandate Flag","body","bank_name"
        ]
        return pd.DataFrame(columns=cols)

    parsed = trans_df.apply(
        lambda r: parse_transaction(r.get("body", ""), r.get("address", "")),
        axis=1,
        result_type="expand"
    )

    # attach original columns if present
    for c in ["_id", "date", "body", "bank_name"]:
        parsed[c] = trans_df[c].values if c in trans_df.columns else None

    cols = [
        "_id","date","SenderID","Financial Product","Transaction Type","Transaction Subtype",
        "Amount","Balance","Payee","Reference Number","Card Number","Account Number",
        "Transaction Channel","Context","Mandate Flag","body","bank_name"
    ]
    parsed = parsed[[c for c in cols if c in parsed.columns]]

    return parsed