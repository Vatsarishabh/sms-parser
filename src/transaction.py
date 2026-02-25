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
# 4) Amount extraction
# -----------------------------
def extract_txn_amount(text: str):
    """
    Extract amount tied to a real transaction verb
    (credited/debited/paid/spent/received/withdrawn/transferred).
    """
    if not isinstance(text, str) or not text.strip():
        return None

    t = text

    # Amount needs a txn verb nearby (credited/debited/paid/spent/received/withdrawn/transferred)
    # Handles:
    #   "Rs 1,234 credited"            → pattern 1
    #   "debited by INR 500"           → pattern 2
    #   "INR 550 has been DEBITED"     → pattern 3  (Canara, SBI style)
    #   "amount of INR 550 debited"    → pattern 4
    #   "Amt Rs. 99 paid"              → pattern 5
    _TXN_VERB = r"(?:credited|debited|paid|spent|received|withdrawn|transferred)"
    _CCY      = r"(?:rs|inr)\.?"
    _AMT      = r"([\d,]+(?:\.\d{1,2})?)"
    _FILLER   = r"(?:\s+(?:has\s+been|have\s+been|is|are|was|been|successfully))*"

    amount_patterns = [
        # INR 550 credited  /  INR 550 has been DEBITED
        rf"{_CCY}\s*{_AMT}\s*{_FILLER}\s*{_TXN_VERB}\b",
        # debited by INR 500  /  credited INR 500
        rf"{_TXN_VERB}\s*(?:by\s*)?{_CCY}\s*{_AMT}\b",
        # amount of INR 550 debited/credited
        rf"amount\s+of\s+{_CCY}\s*{_AMT}\s*{_FILLER}\s*{_TXN_VERB}\b",
        # Amt/Amount Rs. 99 paid
        rf"\bamt\b[\s:.-]*{_CCY}?\s*{_AMT}\b.*?\b{_TXN_VERB}\b",
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

    # Handles:
    #   "Bal: INR 83,123.50"  /  "Avail.bal INR 83,123.50"  /  "Balance Rs 5000"
    #   The currency symbol may come BEFORE or AFTER the balance keyword
    p_balance = (
        r"(?:balance|bal|avl|avail\.bal|avail\s+bal|avl\s+bal)"
        r"[\s\.:]* "
        r"(?:(?:rs|inr)\.?\s*)?"
        r"([\d,]+(?:\.\d{1,2})?)"
    )
    b = first_group(p_balance, text)
    return b.replace(",", "") if b else None


def extract_avl_limit(text: str):
    """
    Extract the Available Credit Limit from a credit-card spend SMS.
    Handles patterns like:
      "Avl Limit: INR 69,404.64"
      "Available Limit: Rs 50000"
      "Avl Lmt INR 1,23,456.78"
    Returns numeric string without commas, or None.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    p = (
        r"(?:avl|avail(?:able)?)\s*li?mi?t[:\s]*"
        r"(?:(?:inr|rs)\.?\s*)?"
        r"([\d,]+(?:\.\d{1,2})?)"
    )
    m = re.search(p, text, re.I)
    if m:
        return m.group(1).replace(",", "")
    return None


def extract_last_bill(text: str):
    """
    Extract the total bill/statement due amount from a credit-card statement SMS.
    Handles patterns like:
      "Total of Rs 9,977.40 or minimum of Rs 500.00 is due by 23-MAY-25"
      "Your bill of INR 5,430 is due"
      "Total Amount Due: INR 12,345.67"
    Returns numeric string without commas, or None.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    patterns = [
        # "Total of Rs 9,977.40 ... is due"
        r"total\s+of\s+(?:rs|inr)\.?\s*([\d,]+(?:\.\d{1,2})?)",
        # "Total Amount Due: INR 12,345"
        r"total\s+(?:amount\s+)?due[:\s]+(?:(?:rs|inr)\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
        # "bill of INR 5,430"
        r"bill\s+(?:amount\s+)?(?:of\s+)?(?:(?:rs|inr)\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
        # "Amount Due Rs 4,000"
        r"amount\s+due[:\s]+(?:(?:rs|inr)\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).replace(",", "")
    return None

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
# 6) parse_transaction
# (offer/marketing messages are filtered upstream in promotion_analysis)
# -----------------------------
def parse_transaction(body, address):
    t = clean_text(body)

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

    avl_limit = extract_avl_limit(t)
    last_bill  = extract_last_bill(t)

    return {
        "SenderID": address,
        "Financial Product": product,
        "Transaction Type": txn_type,
        "Transaction Subtype": subtype,
        "Amount": amount,
        "Balance": balance,
        "Avl Limit": avl_limit,
        "Last Bill": last_bill,
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
            "Amount","Balance","Avl Limit","Last Bill","Payee","Reference Number",
            "Card Number","Account Number","Transaction Channel","Context","Mandate Flag",
            "body","bank_name"
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
        "Amount","Balance","Avl Limit","Last Bill","Payee","Reference Number",
        "Card Number","Account Number","Transaction Channel","Context","Mandate Flag",
        "body","bank_name"
    ]
    parsed = parsed[[c for c in cols if c in parsed.columns]]

    return parsed