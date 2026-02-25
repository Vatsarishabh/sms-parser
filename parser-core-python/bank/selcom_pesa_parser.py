import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class SelcomPesaParser(BankParser):
    """
    Parser for Selcom Pesa (Tanzania) mobile money SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Selcom Pesa"

    def get_currency(self) -> str:
        return "TZS"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "SELCOM" in up or "SELCOMPESA" in up

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"TZS\s+([0-9,]+(?:\.[0-9]{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "you have received" in low: return TransactionType.INCOME
        if any(k in low for k in ["you have sent", "you have paid", "you have withdrawn"]): return TransactionType.EXPENSE
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"from\s+([A-Z][A-Za-z\s]+?)(?:\s+-\s+[^(]+)?\s*\([^)]+\)", message, re.I)
        if m1:
            mer = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m2 = re.search(r"to\s+([A-Z][A-Za-z\s]+?)(?:\s+-\s+[^(]+)?\s*\([^)]+\)", message, re.I)
        if m2:
            mer = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m3 = re.search(r"paid\s+TZS\s+[0-9,]+(?:\.[0-9]{2})?\s+to\s+([A-Za-z0-9\s]+?)(?:\s+using|\s+on)", message, re.I)
        if m3:
            mer = self.clean_merchant_name(m3.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        if "withdrawn" in message.lower() and "atm" in message.upper():
            m4 = re.search(r"at\s+ATM\s+-?\s*([^u]+?)(?:\s+using|$)", message, re.I)
            if m4:
                loc = m4.group(1).strip()
                return f"ATM - {loc}" if loc else "ATM Withdrawal"
            return "ATM Withdrawal"
            
        m5 = re.search(r"to\s+([A-Z][A-Za-z\s]+?)(?:\s+on\s+|\s*$)", message, re.I)
        if m5:
            mer = self.clean_merchant_name(m5.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        return None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Updated balance is TZS\s+([0-9,]+(?:\.[0-9]{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"^([A-Z0-9]{8,9})\s+(?:Confirmed|Accepted)", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"TIPS\s+Reference[:\s]+([A-Z0-9]+)", message, re.I)
        if m2: return m2.group(1)
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"card\s+ending\s+(?:with\s+)?(\d{4})", message, re.I)
        return m.group(1) if m else None

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "confirmed" not in low and "accepted" not in low: return False
        kw = ["you have received", "you have sent", "you have paid", "you have withdrawn", "updated balance"]
        return any(k in low for k in kw)

    def detect_is_card(self, message: str) -> bool:
        low = message.lower()
        return "card ending" in low or "using your card" in low

    def clean_merchant_name(self, merchant: str) -> str:
        m = re.sub(r"\s*\(.*?\)\s*$", "", merchant)
        m = re.sub(r"\s+-\s+.*$", "", m)
        m = re.sub(r"\s+on\s+\d{4}.*", "", m)
        m = re.sub(r"\s*-\s*$", "", m)
        return m.strip()
