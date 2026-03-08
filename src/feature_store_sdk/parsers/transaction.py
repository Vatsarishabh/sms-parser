"""
transaction.py
--------------
Transaction SMS parser for the feature_store_sdk.
Extracts structured transaction features from SMS body text.
"""

import re

from ..models import TransactionParsed


def clean_text(text):
    if not isinstance(text, str):
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


def extract_reference(text):
    m = re.search(r"([A-Z]{3,6}\d{11}|\b\d{10,12}\b|Ref[:\s-]*(\d+)|UTR[:\s-]*(\d+))", text, re.I)
    if not m:
        return None
    g = m.groups()
    ref = next((x for x in g if x is not None), m.group(0))
    ref = re.sub(r'(Ref|UTR)[:\s-]*', '', ref, flags=re.I).strip()
    return ref or None


def extract_txn_amount(text: str):
    """
    Extract amount tied to a real transaction verb
    (credited/debited/paid/spent/received/withdrawn/transferred).
    """
    if not isinstance(text, str) or not text.strip():
        return None

    t = text

    _TXN_VERB = r"(?:credited|debited|paid|spent|received|withdrawn|transferred)"
    _CCY      = r"(?:rs|inr)\.?"
    _AMT      = r"([\d,]+(?:\.\d{1,2})?)"
    _FILLER   = r"(?:\s+(?:has\s+been|have\s+been|is|are|was|been|successfully))*"

    amount_patterns = [
        rf"{_CCY}\s*{_AMT}\s*{_FILLER}\s*{_TXN_VERB}\b",
        rf"{_TXN_VERB}\s*(?:by\s*)?{_CCY}\s*{_AMT}\b",
        rf"amount\s+of\s+{_CCY}\s*{_AMT}\s*{_FILLER}\s*{_TXN_VERB}\b",
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
    """
    if not isinstance(text, str) or not text.strip():
        return None
    patterns = [
        r"total\s+of\s+(?:rs|inr)\.?\s*([\d,]+(?:\.\d{1,2})?)",
        r"total\s+(?:amount\s+)?due[:\s]+(?:(?:rs|inr)\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
        r"bill\s+(?:amount\s+)?(?:of\s+)?(?:(?:rs|inr)\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
        r"amount\s+due[:\s]+(?:(?:rs|inr)\.?\s*)?([\d,]+(?:\.\d{1,2})?)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).replace(",", "")
    return None


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


def parse_transaction(body, address):
    t = clean_text(body)

    p_acc   = r"(?:a/c|ac|acc|no|card|wallet|X+|[\*]+)\s*(\d{3,4})\b"
    p_card4 = r"(?:card|ending\s+with)\s*(?:X+|[\*]+)?\s*(\d{4})\b"

    acc   = first_group(p_acc, t)
    card4 = first_group(p_card4, t)

    amount  = extract_txn_amount(t)
    balance = extract_balance(t)

    card_number = card4 if card4 else (acc if ("card" in t.lower()) else None)
    ref = extract_reference(t)

    mandate_flag = bool(re.search(r"\b(mandate|standing\s+instruction|autopay|si)\b", t, re.I))

    # Transaction Type
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
    elif re.search(r"\b(card|visa|mastercard|cc|dc|credit\s+card|debit\s+card)\b", t, re.I):
        channel = "Card"
    elif re.search(r"(?<!/c\s)(?<!a/c\s)(?<!ac\s)(?<!acct\s)\bXX\d{4}\b", t, re.I) and not re.search(r"\ba/c\b", t, re.I):
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
    elif (re.search(r"\b(card|visa|mastercard|cc|dc|credit\s+card|debit\s+card)\b", t, re.I) or "card" in t.lower()) and not re.search(r"\ba/c\b", t, re.I):
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


def _safe_float(value):
    """Convert a string or numeric value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_transaction_model(body, address, base_fields=None):
    """
    Parse a transaction SMS and return a TransactionParsed dataclass instance.

    Parameters
    ----------
    body : str
        The SMS body text.
    address : str
        The sender address / sender ID.
    base_fields : dict, optional
        Pre-computed SMSBase fields (entity_name, header_code, traffic_type,
        occurrence_tag, alphabetical_tag, tag_count, timestamp, etc.)
        to populate on the model.

    Returns
    -------
    TransactionParsed
    """
    result = parse_transaction(body, address)

    # Determine payer via extract_payer_payee
    payer, _ = extract_payer_payee(clean_text(body))

    # Determine salary flag
    txn_type = result.get("Transaction Type")
    salary = is_salary_credit(body, txn_type)

    # Build the dataclass keyword arguments from the parsed dict
    kwargs = dict(
        raw_body=body or "",
        sender_address=address or "",
        txn_type=txn_type,
        txn_subtype=result.get("Transaction Subtype"),
        amount=_safe_float(result.get("Amount")),
        balance=_safe_float(result.get("Balance")),
        avl_limit=_safe_float(result.get("Avl Limit")),
        last_bill=_safe_float(result.get("Last Bill")),
        account_number=result.get("Account Number"),
        card_number=result.get("Card Number"),
        financial_product=result.get("Financial Product"),
        txn_channel=result.get("Transaction Channel"),
        reference_number=result.get("Reference Number"),
        payee=result.get("Payee"),
        payer=payer,
        context=result.get("Context"),
        mandate_flag=result.get("Mandate Flag", False),
        is_salary=salary,
    )

    # Overlay any pre-computed SMSBase fields
    if base_fields and isinstance(base_fields, dict):
        for key, value in base_fields.items():
            if hasattr(TransactionParsed, key):
                kwargs[key] = value

    return TransactionParsed(**kwargs)
