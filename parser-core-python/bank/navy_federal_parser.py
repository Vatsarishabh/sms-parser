import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class NavyFederalParser(BankParser):
    """
    Parser for Navy Federal Credit Union (NFCU) - handles USD debit card and credit card transactions.
    """

    def get_bank_name(self) -> str:
        return "Navy Federal Credit Union"

    def get_currency(self) -> str:
        return "USD"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up in ["NFCU", "NAVYFED"] or "NAVY FEDERAL" in up or "NAVYFEDERAL" in up or bool(re.match(r"^[A-Z]{2}-NFCU-[A-Z]$", up))

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"Transaction for \$([0-9,]+(?:\.[0-9]{2})?)\s+was approved",
                r"Transaction for \$([0-9,]+(?:\.[0-9]{2})?)\s+was declined",
                r"for \$([0-9,]+(?:\.[0-9]{2})?)\s+was approved",
                r"for \$([0-9,]+(?:\.[0-9]{2})?)\s+was declined"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"on (?:debit|credit) card \d{4} at (.+?)\s+at \d{2}:\d{2}", message, re.I)
        if m1: return m1.group(1).strip()
        m2 = re.search(r"on (?:debit|credit) card \d{4} at (.+?)(?:\.|$)", message, re.I)
        if m2:
            mer = m2.group(1).strip()
            return re.sub(r"Txt STOP.*", "", mer, flags=re.I).strip()
        return super().extract_merchant(message, sender)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "was approved" in low: return TransactionType.EXPENSE
        if "was declined" in low: return None
        if "payment received" in low or "deposit" in low: return TransactionType.CREDIT
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"on debit card (\d{4})", r"on credit card (\d{4})", r"(?:debit|credit) card (\d{4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_account_last4(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        kw = ["transaction for", "was approved on", "was declined on"]
        if any(k in low for k in kw):
            if "was declined" in low: return False
            return True
        return super().is_transaction_message(message)

    def detect_is_card(self, message: str) -> bool:
        low = message.lower()
        if "debit card" in low or "credit card" in low: return True
        return super().detect_is_card(message)
