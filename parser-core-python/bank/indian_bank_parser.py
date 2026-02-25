import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class IndianBankParser(BaseIndianBankParser):
    """
    Parser for Indian Bank.
    """

    def get_bank_name(self) -> str:
        return "Indian Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        if any(k in norm for k in ["INDIAN BANK", "INDIANBANK", "INDIANBK"]): return True
        pats = [r"^[A-Z]{2}-INDBNK-S$", r"^[A-Z]{2}-INDBNK-[TPG]$", r"^[A-Z]{2}-INDBNK$", "INDBNK", "INDIAN"]
        return any(re.match(p, norm) for p in pats) or norm in pats

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"debited\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"credited\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s+credited\s+to",
                r"withdrawn\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"UPI\s+payment\s+of\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"to\s+([^.\n]+?)(?:\.\s*UPI:|UPI:|$)", message, re.I)
        if m1:
            merch = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
            
        m2 = re.search(r"from\s+([^.\n]+?)(?:\.\s*UPI:|UPI:|$)", message, re.I)
        if m2:
            merch = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
            
        m3 = re.search(r"VPA\s+([\w.-]+@[\w]+)", message, re.I)
        if m3: return self.clean_merchant_name(m3.group(1).split("@")[0])
        
        m4 = re.search(r"ATM\s+(?:withdrawal\s+)?at\s+([^.\n]+?)(?:\s+on|$)", message, re.I)
        if m4:
            loc = self.clean_merchant_name(m4.group(1).strip())
            if self.is_valid_merchant_name(loc): return f"ATM - {loc}"
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"A/c\s+\*(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"Account\s+X*(\d{4})", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"A/c\s+ending\s+(\d{4})", message, re.I)
        if m3: return m3.group(1)
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"UPI:(\d+)", message, re.I) or \
            re.search(r"UPI\s+Ref\s+no\s+(\d+)", message, re.I) or \
            re.search(r"Ref\s+No\.?\s*(\w+)", message, re.I) or \
            re.search(r"Transaction\s+ID:?\s*(\w+)", message, re.I)
        return m.group(1) if m else super().extract_reference(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Bal\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"Available\s+Balance:?\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "debited" in low or "withdrawn" in low: return TransactionType.EXPENSE
        if "upi payment" in low and "received" not in low: return TransactionType.EXPENSE
        if any(k in low for k in ["credited", "deposited", "received"]): return TransactionType.INCOME
        return super().extract_transaction_type(message)
