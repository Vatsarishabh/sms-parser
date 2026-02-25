import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class IndianOverseasBankParser(BankParser):
    """
    Parser for Indian Overseas Bank (IOB) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Indian Overseas Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return "IOB" in norm or "IOBCHN" in norm

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"credited\s+by\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"debited\s+by\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"credited\s+with\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"debited\s+for\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(k in low for k in ["credited by", "credited with", "is credited"]): return TransactionType.INCOME
        if any(k in low for k in ["debited by", "debited for", "is debited"]): return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"from\s+([^(]+?)(?:\(UPI|$)", message, re.I)
        if m1:
            payer = m1.group(1).strip()
            if "@" in payer:
                parts = payer.split("-")
                if len(parts) >= 2:
                    name = self.clean_merchant_name(parts[0].strip())
                    upi_id = parts[1].strip()
                    return f"UPI - {name} ({upi_id})"
                return f"UPI - {self.clean_merchant_name(payer)}"
            cleaned = self.clean_merchant_name(payer)
            if self.is_valid_merchant_name(cleaned): return cleaned
            
        m2 = re.search(r"Payer\s+Remark\s*-\s*([^-]+)", message, re.I)
        if m2:
            rem = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(rem) and rem.lower() != "paid via supe":
                return rem
                
        if "debited" in message.lower():
            m3 = re.search(r"(?:to|for)\s+([^,.-]+)", message, re.I)
            if m3:
                merch = self.clean_merchant_name(m3.group(1).strip())
                if self.is_valid_merchant_name(merch): return merch
                
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"a/c\s+no\.\s+[X]*(\d{2,4})", message, re.I)
        if m:
            val = m.group(1)
            return val[-4:] if len(val) >= 4 else val
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"\(UPI\s+Ref\s+no\s+(\d+)\)", message, re.I) or \
            re.search(r"UPI\s+Ref\s+no\s+(\d+)", message, re.I)
        return m.group(1) if m else super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "verification", "request", "failed"]): return False
        kw = ["is credited by", "is debited by", "credited with", "debited for"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
