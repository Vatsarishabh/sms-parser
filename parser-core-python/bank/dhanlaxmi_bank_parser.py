import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class DhanlaxmiBankParser(BaseIndianBankParser):
    """
    Parser for Dhanlaxmi Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Dhanlaxmi Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return "DHANBK" in norm or "DHANLAXMI" in norm or re.match(r"^[A-Z]{2}-DHANBK(-?[A-Z])?$", norm)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"INR\s+([0-9,]+(?:\.\d{2})?)\s+is\s+(?:debited|credited)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        m = re.search(r"(?:credited|debited)\s+for\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(kw in low for kw in ["is debited", "debited from", "debited from a/c"]): return TransactionType.EXPENSE
        if any(kw in low for kw in ["is credited", "credited to", "credited for"]): return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"A/c\s+X+(\d{4})", message, re.I)
        if m: return m.group(1)
        m = re.search(r"a/c\s+no\.\s*X+(\d{4})", message, re.I)
        if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Aval\s+Bal\s+is\s+INR\s+([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        if "upi txn" in message.lower():
            m = re.search(r"Payment\s+from\s+([^/]+)", message, re.I)
            if m:
                merch = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(merch): return merch
            
            m = re.search(r"payment\s+on\s+(\w+)", message, re.I)
            if m:
                merch = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(merch): return merch
                
            return "UPI Payment"
            
        if "debited from a/c" in message.lower() and "credited" in message.lower(): return "Internal Transfer"
        return super().extract_merchant(message, sender)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"UPI\s+Ref\s+no\s+(\d+)", message, re.I)
        if m: return m.group(1)
        
        m = re.search(r"UPI\s+TXN:\s*/(\d+)", message, re.I)
        if m: return m.group(1)
        
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(kw in low for kw in ["otp", "one time password", "verification code"]): return False
        kw = ["is debited from", "is credited to", "credited for", "debited from a/c"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
