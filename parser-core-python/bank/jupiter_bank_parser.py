import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser

class JupiterBankParser(BankParser):
    """
    Parser for Jupiter Bank (CSB Bank partner) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Jupiter"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        pats = [r"^[A-Z]{2}-JTEDGE-S$", r"^[A-Z]{2}-JTEDGE-T$", r"^[A-Z]{2}-JTEDGE$"]
        return any(re.match(p, up) for p in pats)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"Rs\.?\s*([0-9,]+(?:\.\d{2})?)\s+debited", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        m2 = re.search(r"Rs\.?\s*([0-9,]+(?:\.\d{2})?)\s+credited", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "edge csb bank rupay credit card" in low or "jupiter csb edge" in low or "credit card" in low:
            return "Credit Card Payment"
        if "upi" in low: return "UPI Transaction"
        return super().extract_merchant(message, sender) or "Jupiter Transaction"

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"ending\s+(\d{4})", message, re.I) or re.search(r"Card\s+ending\s+(\d{4})", message, re.I)
        return m.group(1) if m else super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"UPI\s+Ref\s+no\.?\s*([A-Za-z0-9]+)", message, re.I)
        return m.group(1) if m else super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "jupiter" in low or "csb" in low: return super().is_transaction_message(message)
        return super().is_transaction_message(message)
