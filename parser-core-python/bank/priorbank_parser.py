import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class PriorbankParser(BankParser):
    """
    Parser for Priorbank (Belarus) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Priorbank"

    def get_currency(self) -> str:
        return "BYN"

    def can_handle(self, sender: str) -> bool:
        return "PRIORBANK" in sender.upper()

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Oplata\s+([0-9]+(?:\.\d{2})?)\s+BYN", message, re.I)
        if m:
            try: return Decimal(m.group(1))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "oplata" in low: return TransactionType.EXPENSE
        if "popolnenie" in low or "zachislenie" in low: return TransactionType.INCOME
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r'"([^"]+)"', message, re.I)
        if m1:
            mer = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m2 = re.search(r"BYN\.\s+([^.]+?)\.\s+Dostupno", message, re.I)
        if m2:
            mer = m2.group(1).strip()
            mer = re.sub(r"^BLR\s+", "", mer, flags=re.I)
            mer = self.clean_merchant_name(mer)
            if self.is_valid_merchant_name(mer): return mer
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"Karta\s+[6-9][\*]+(\d{4})", message, re.I)
        return m.group(1) if m else None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Dostupno:\s+([0-9]+(?:\.\d{2})?)\s+BYN", message, re.I)
        if m:
            try: return Decimal(m.group(1))
            except (InvalidOperation, ValueError): pass
        return None

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "kod", "parol"]): return False
        kw = ["oplata", "karta", "dostupno"]
        return any(k in low for k in kw)
