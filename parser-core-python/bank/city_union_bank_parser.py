import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class CityUnionBankParser(BaseIndianBankParser):
    """
    Parser for City Union Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "City Union Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return any(k in norm for k in ["CUBANK", "CUBLTD", "CUB"])

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [re.compile(r"debited\s+for\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)", re.I),
                re.compile(r"credited\s+for\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)", re.I),
                re.compile(r"credited\s+with\s+INR\s*([0-9,]+(?:\.\d{2})?)", re.I)]
        for p in pats:
            m = p.search(message)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(kw in low for kw in ["is debited", "debited for", "debited from"]): return TransactionType.EXPENSE
        if any(kw in low for kw in ["is credited", "credited for", "credited with", "credited to", "neft trf"]): return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "neft trf" in low:
            m = re.search(r"BY\s+NEFT\s+TRF:([^:]+)", message, re.I)
            if m: return f"NEFT - {self.clean_merchant_name(m.group(1).strip())}"
            return "NEFT Transfer"

        if "upi ref" in low:
            to_m = re.search(r"credited\s+to\s+a/c\s+no\.\s+([A-Z0-9]+)", message, re.I)
            if to_m:
                val = to_m.group(1)
                return f"UPI Transfer to A/C XX{val[-4:] if len(val) >= 4 else val}"
            
            from_m = re.search(r"debited\s+from\s+a/c\s+no\.\s+([A-Z0-9]+)", message, re.I)
            if from_m:
                val = from_m.group(1)
                return f"UPI Transfer from A/C XX{val[-4:] if len(val) >= 4 else val}"
            
            return "UPI Transfer"

        if "credited to a/c" in low or "debited from a/c" in low: return "Account Transfer"
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"Your\s+a/c\s+no\.\s+[X]*(\d{3,4})", r"Savings\s+No\s+[X]*(\d{3,4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                val = m.group(1)
                return val[-4:] if len(val) >= 4 else val
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Avl\s+Bal\s+([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"\(UPI\s+Ref\s+no\s+(\d+)\)", message, re.I)
        if m: return m.group(1)
        
        m = re.search(r"NEFT[:/]\s*([A-Z0-9]+)", message, re.I)
        if m: return m.group(1)
        
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(kw in low for kw in ["otp", "verification", "request"]): return False
        kw = ["is debited for", "is credited for", "credited with", "neft trf"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
