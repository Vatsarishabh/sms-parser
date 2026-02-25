import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from .base_indian_bank_parser import BaseIndianBankParser

class CanaraBankParser(BaseIndianBankParser):
    """
    Parser for Canara Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Canara Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return "CANBNK" in norm or "CANARA" in norm

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Rs\.?\s*([\d,]+(?:\.\d{2})?)\s+paid", message, re.IGNORECASE)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        
        m = re.search(r"INR\s+([\d,]+(?:\.\d{2})?)\s+has\s+been\s+DEBITED", message, re.IGNORECASE)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"\sto\s+([^,]+?)(?:,\s*UPI|\.|-Canara)", message, re.IGNORECASE)
        if m:
            merch = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
            
        if "DEBITED" in message.upper(): return "Canara Bank Debit"
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"(?:account|A/C)\s+(?:XX|X\*+)?(\d{3,4})", message, re.IGNORECASE)
        if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"(?:Total\s+)?Avail\.?bal\s+INR\s+([\d,]+(?:\.\d{2})?)", message, re.IGNORECASE)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"UPI\s+Ref\s+(\d+)", message, re.IGNORECASE)
        if m: return m.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        lower = message.lower()
        if "failed due to" in lower: return False
        if any(kw in lower for kw in ["paid thru", "has been debited", "has been credited"]): return True
        return super().is_transaction_message(message)
