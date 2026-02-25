import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class TelebirrParser(BankParser):
    """
    Parser for Telebirr - handles ETB currency transactions.
    """

    def get_bank_name(self) -> str:
        return "Telebirr"

    def get_currency(self) -> str:
        return "ETB"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper().strip()
        if up == "127" or "127" in up: return True
        pats = [r"^[A-Z]{2}-127-[A-Z]$", r"^127-[A-Z0-9]+$", r"^[A-Z0-9]+-127$"]
        return any(re.match(p, up) for p in pats)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"ETB\s+([0-9,]+(?:\.[0-9]{2})?)\s",
                r"ETB\s*([0-9,]+(?:\.[0-9]{2})?)(?:\s|$|\.)",
                r"(?:Credited|debited|transfered)\s+(?:with\s+)?ETB\s+([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "deposited etb" in low and "to your saving account" in low: return TransactionType.EXPENSE
        if "withdraw etb" in low and "from your saving account" in low: return TransactionType.INCOME
        if "you have received" in low: return TransactionType.INCOME
        if "you have paid" in low: return TransactionType.EXPENSE
        if "you have transferred" in low: return TransactionType.EXPENSE
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"deposited\s+ETB\s+[0-9,]+(?:\.[0-9]{2})?\s+to\s+your\s+(.+?)\s+on\s+\d{2}/\d{2}/\d{4}", message, re.I)
        if m1: return m1.group(1).strip()
        
        m2 = re.search(r"withdraw(?:n)?\s+ETB\s+[0-9,]+(?:\.[0-9]{2})?\s+from\s+your\s+(.+?)\s+on\s+\d{2}/\d{2}/\d{4}", message, re.I)
        if m2: return m2.group(1).strip()
        
        m3 = re.search(r"from\s+([A-Za-z\s]+Bank)\s+to\s+your", message, re.I)
        if m3:
            mer = m3.group(1).strip()
            if self.is_valid_merchant_name(mer): return mer
            
        m4 = re.search(r"paid\s+ETB\s+[0-9,]+(?:\.[0-9]{2})?\s+to\s+([^,\n]+?)(?=\s+on\s+\d{2}/\d{2}/\d{4}|\.\s+Your\s+transaction|$)", message, re.I)
        if m4: return m4.group(1) # Note: Kotlin code had some extra logic for space, but group(1) should be enough
        
        m5 = re.search(r"for\s+goods\s+purchased\s+from\s+([^,\n]+?)(?:\s+on\s+\d{2}/\d{2}/\d{4}|\.\s+Your\s+transaction|$)", message, re.I)
        if m5: return m5.group(1).strip()
        
        m6 = re.search(r"for\s+package\s+([^,\n]+?)(?:\s+purchase\s+made|\s+on\s+\d{2}/\d{2}/\d{4}|\.\s+Your\s+transaction|$)", message, re.I)
        if m6:
            pkg = m6.group(1).strip()
            mp = re.search(r"purchase\s+made\s+for\s+(\d+)", message, re.I)
            if mp: pkg += f" purchase made for {mp.group(1)}"
            return pkg
            
        m7 = re.search(r"transferred\s+[^,\n]+?\s+to\s+([^,\n]+?)(?:\s+on\s+\d{2}/\d{2}/\d{4}|\.|$)", message, re.I)
        if m7:
            mer = m7.group(1).strip()
            if "(" in mer and ")" in mer: return mer
            mer = self.clean_merchant_name(mer)
            if self.is_valid_merchant_name(mer): return mer
            
        m8 = re.search(r"from\s+(?!your\s+account)([^,\n]+?)(?:\s+on\s+\d{2}/\d{2}/\d{4}|\s+to\s+your|\.|$)", message, re.I)
        if m8:
            mer = m8.group(1).strip()
            mer = re.sub(r"([A-Za-z\s]+)\((\d+\*+\d+)\)", r"\1 (\2)", mer)
            if "(" in mer and ")" in mer: return mer
            mer = self.clean_merchant_name(mer)
            if self.is_valid_merchant_name(mer): return mer
            
        m9 = re.search(r"to\s+([^,\n]+?)(?:\s+on\s+\d{2}/\d{2}/\d{4}|\.|$)", message, re.I)
        if m9:
            mer = m9.group(1).strip()
            if "(" in mer: return mer
            mer = self.clean_merchant_name(mer)
            if self.is_valid_merchant_name(mer): return mer
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"Dear\s+\[([^\]]+)\]", message, re.I)
        return f"[{m.group(1)}]" if m else super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"E-Money Account\s+balance is ETB\s+([0-9,]+(?:\.[0-9]{2})?)",
                r"current balance is ETB\s+([0-9,]+(?:\.[0-9]{2})?)",
                r"telebirr account balance is\s+ETB\s+([0-9,]+(?:\.[0-9]{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"bank transaction number is\s+([A-Z0-9]+)",
                r"by transaction number\s+([A-Z0-9]+)",
                r"(?:your\s+)?transaction number is\s+([A-Z0-9]+)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        kw = ["dear", "you have received", "you have paid", "you have transferred", "current balance", "e-money account balance", "telebirr account balance", "thank you for using telebirr", "etb", "transaction number"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
