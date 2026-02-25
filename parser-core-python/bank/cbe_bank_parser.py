import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class CBEBankParser(BankParser):
    """
    Parser for Commercial Bank of Ethiopia (CBE) - handles ETB currency transactions.
    """

    def get_bank_name(self) -> str:
        return "Commercial Bank of Ethiopia"

    def get_currency(self) -> str:
        return "ETB"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "CBE" or "COMMERCIALBANK" in up or "CBEBANK" in up or bool(re.match(r"^[A-Z]{2}-CBE-[A-Z]$", up))

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"ETB\s+([0-9,]+(?:\.[0-9]{2})?)\s",
                r"ETB\s*([0-9,]+(?:\.[0-9]{2})?)(?:\s|$|\.)",
                r"(?:Credited|debited|transfered)\s+(?:with\s+)?ETB\s+([0-9,]+(?:\.[0-9]{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "has been credited" in low or "credited with" in low: return TransactionType.INCOME
        if "has been debited" in low or "debited with" in low: return TransactionType.EXPENSE
        if "you have transfered" in low or "transferred" in low: return TransactionType.EXPENSE
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"from\s+([^,\s]+\*{0,3}[^,\s]*)", message, re.I)
        if m1:
            mer = m1.group(1).strip()
            if mer: return self.clean_merchant_name(mer.replace("*", ""))
            
        m2 = re.search(r"to\s+([^,\s]+\*{0,5}[^,\s]*)", message, re.I)
        if m2:
            mer = m2.group(1).strip()
            if mer: return self.clean_merchant_name(mer.replace("*", ""))
            
        if "s.charge" in message.lower() or "service charge" in message.lower():
            return "Service Charge"
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"Account\s+\d?\*+(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"your account\s+\d?\*+(\d{4})", message, re.I)
        if m2: return m2.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Current Balance is ETB\s+([0-9,]+(?:\.[0-9]{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"Ref No\s+(\*{0,9}[A-Z0-9]+)", message, re.I)
        if m1:
            ref = m1.group(1).replace("*", "")
            if ref: return ref
        m2 = re.search(r"id=([A-Z0-9]+)", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"on\s+(\d{2}/\d{2}/\d{4}\s+at\s+\d{2}:\d{2}:\d{2})", message, re.I)
        if m3: return m3.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        kw = ["dear", "your account", "has been credited", "has been debited", "you have transfered", "current balance", "thank you for banking with cbe", "etb"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
