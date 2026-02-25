import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class ZemenBankParser(BankParser):
    """
    Parser for Zemen Bank - handles ETB currency transactions.
    """

    def get_bank_name(self) -> str:
        return "Zemen Bank"

    def get_currency(self) -> str:
        return "ETB"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper().replace(" ", "")
        return up == "ZEMENBANK" or bool(re.match(r"^[A-Z]{2}-ZEMENBANK-[A-Z]$", sender.upper().strip()))

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"(?:ETB|Birr)\s+([0-9,]+(?:\.[0-9]{1,2})?)", message, re.I)
        if m: return self.parse_scaled_amount(m.group(1))
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "has been credited" in low or "credited with" in low: return TransactionType.INCOME
        if "has been debited" in low or "debited with" in low: return TransactionType.EXPENSE
        if any(k in low for k in ["fund transfer has been made from", "pos transaction has been made from", "atm cash withdrawal has been made from", "you have transfered", "you have transferred"]):
            return TransactionType.EXPENSE
        if "transferred" in low and "from a/c" in low: return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"from\s+(telebirr wallet\s+\d+)\s+with reference", message, re.I)
        if m1: return m1.group(1)
        
        m2 = re.search(r"to\s+(telebirr wallet\s+\d+)\s+with reference", message, re.I)
        if m2: return m2.group(1)
        
        m3 = re.search(r"to\s+A/c\s+of\s+(\d{6,})", message, re.I)
        if m3: return m3.group(1).strip()
        
        m4 = re.search(r"from\s+([^,\.]+?)\s+with reference", message, re.I)
        if m4:
            mer = self.clean_merchant_name(m4.group(1)).strip()
            if mer and self.is_valid_merchant_name(mer): return mer
            
        m5 = re.search(r"pos purchase transaction at\s+(.+?)\s+on\s+\d{1,2}-[A-Za-z]{3}-\d{4}", message, re.I)
        if m5:
            mer = self.clean_merchant_name(m5.group(1)).strip()
            if mer: return mer
            
        m6 = re.search(r"transaction POS location is\s+(.+?)\s*\. ", message, re.I)
        if m6: return m6.group(1).strip()
        
        m7 = re.search(r"to\s+(.+?)\s+with reference", message, re.I)
        if m7: return m7.group(1).strip()
        
        m8 = re.search(r"transaction ATM location is\s+(.+?)\s*\. ", message, re.I)
        if m8: return m8.group(1).strip()
        
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"\b\d{3}x+(\d{4})\b", r"\(\d{3}x+(\d{4})\)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Your\s+Current\s+Balance\s+is\s+(?:ETB|Birr)\s+([0-9,]+(?:\.[0-9]{1,2})?)",
                r"A/c\s+Available\s+Bal\.\s+is\s+(?:ETB|Birr)\s+([0-9,]+(?:\.[0-9]{1,2})?)",
                r"Your\s+available\s+balance\s+is\s+(?:ETB|Birr)\s+([0-9,]+(?:\.[0-9]{1,2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return self.parse_scaled_amount(m.group(1))
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"transaction reference number is\s+([A-Z0-9]+)", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"with reference\s+([A-Z0-9]+)", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"(https://share\.zemenbank\.com/[^\s]+?/pdf)", message, re.I)
        if m3: return m3.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        keys = ["dear customer", "your account", "has been credited", "has been debited", "fund transfer has been made from", "pos transaction has been made from", "atm cash withdrawal has been made from", "current balance", "available bal.", "thank you for banking with zemen bank", "etb", "birr"]
        if any(k in low for k in keys): return True
        return super().is_transaction_message(message)

    def parse_scaled_amount(self, raw: str) -> Optional[Decimal]:
        try:
            return Decimal(raw.replace(",", "")).setScale(2, rounding=RoundingMode.HALF_UP)
        except (InvalidOperation, ValueError):
            return None
