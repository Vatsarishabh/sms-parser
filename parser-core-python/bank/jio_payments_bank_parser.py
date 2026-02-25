import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class JioPaymentsBankParser(BankParser):
    """
    Parser for Jio Payments Bank (JPB/JPBL) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Jio Payments Bank"

    def can_handle(self, sender: str) -> bool:
        return "JIOPBS" in sender.upper()

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"credited\s+with\s+Rs\.?\s*([\d,]+(?:\.\d{2})?)",
                r"Rs\.?\s*([\d,]+(?:\.\d{2})?)\s+Sent\s+from",
                r"debited\s+with\s+Rs\.?\s*([\d,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"UPI/(?:CR|DR)/[\d]+/([^.\n]+?)(?:\s*\.|$)", message, re.I)
        if m:
            mer = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        low = message.lower()
        if "upi/cr" in low: return "UPI Credit"
        if "upi/dr" in low: return "UPI Payment"
        if "sent from" in low: return "Money Transfer"
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"JPB\s+A/c\s+x(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"from\s+x(\d{4})", message, re.I)
        if m2: return m2.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Avl\.?\s*Bal:\s*Rs\.?\s*([\d,]+(?:\.\d{1,2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"UPI/(?:CR|DR)/(\d+)", message, re.I)
        return m.group(1) if m else super().extract_reference(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "credited" in low or "upi/cr" in low: return TransactionType.INCOME
        if "debited" in low or "upi/dr" in low or "sent from" in low: return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["jpb a/c", "upi/cr", "upi/dr", "sent from"]): return True
        return super().is_transaction_message(message)
