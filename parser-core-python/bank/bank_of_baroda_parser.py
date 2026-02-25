import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class BankOfBarodaParser(BaseIndianBankParser):
    """
    Parser for Bank of Baroda (BOB) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Bank of Baroda"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        if any(k in norm for k in ["BOB", "BARODA", "BOBSMS", "BOBTXN", "BOBCRD"]): return True
        pats = [r"^[A-Z]{2}-BOBSMS-[A-Z]$", r"^[A-Z]{2}-BOBTXN-[A-Z]$", r"^[A-Z]{2}-BOB-[A-Z]$", r"^[A-Z]{2}-BOBCRD-[A-Z]$"]
        if any(re.match(p, norm) for p in pats): return True
        return norm in ["BOB", "BANKOFBARODA"]

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"ALERT:\s*INR\s*([\d,]+(?:\.\d{2})?)\s+is\s+spent",
                r"Rs\.?\s*([\d,]+(?:\.\d{2})?)\s+transferred\s+from",
                r"Rs\.?\s*([\d,]+(?:\.\d{2})?)\s+Dr\.?\s+from",
                r"credited\s+with\s+INR\s+([\d,]+(?:\.\d{2})?)",
                r"Rs\.?\s*([\d,]+(?:\.\d{2})?)\s+Credited\s+to",
                r"Rs\.?\s*([\d,]+(?:\.\d{2})?)\s+.*?Cr\.?\s+to",
                r"Rs\.?\s*([\d,]+(?:\.\d{2})?)\s+deposited\s+in\s+cash"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        m1 = re.search(r"transferred\s+from\s+A/c\s+[^\s]+\s+to:\s*([^.]+?)(?:\.|$)", message, re.I)
        if m1:
            mer_raw = m1.group(1).strip()
            mer = re.split(r"\s+Total\s+Bal", mer_raw, flags=re.I)[0].strip()
            if self.is_valid_merchant_name(mer): return self.clean_merchant_name(mer)
            
        m2 = re.search(r"Cr\.?\s+to\s+([^\s]+@[^\s.] binary=False)", message, re.I) # Fixing regex from input
        # Note: the Kotlin regex was r"Cr\.?\s+to\s+([^\s]+@[^\s.]+)"
        m2 = re.search(r"Cr\.?\s+to\s+([^\s]+@[^\s.]+)", message, re.I)
        if m2:
            vpa = m2.group(1)
            name = vpa.split("@")[0]
            return "UPI Payment" if name.lower() == "redacted" else self.clean_merchant_name(name)
            
        m3 = re.search(r"IMPS/[\d]+\s+by\s+([^.]+?)(?:\s*\.|binary=False|$)", message, re.I)
        m3 = re.search(r"IMPS/[\d]+\s+by\s+([^.]+?)(?:\s*\.|$)", message, re.I)
        if m3:
            mer = self.clean_merchant_name(m3.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        if "upi" in low:
            if "credited" in low: return "UPI Credit"
            if "dr." in low: return "UPI Payment"
        if "imps" in low: return "IMPS Transfer"
        if "deposited in cash" in low: return "Cash Deposit"
        
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"BOBCARD\s+ending\s+(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"A/C\s+X*(\d{6})", message, re.I)
        if m2: return m2.group(1)[-4:]
        m3 = re.search(r"A/c\s+\.+(\d{4})", message, re.I)
        if m3: return m3.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"AvlBal:\s*Rs\.?\s*([\d,]+(?:\.\d{2})?)",
                r"Total\s+Bal:\s*Rs\.?\s*([\d,]+(?:\.\d{2})?)",
                r"Avlbl\s+Amt:\s*Rs\.?\s*([\d,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"Ref:\s*(\d+)", r"UPI\s+Ref\s+No\s+(\d+)", r"IMPS/(\d+)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_reference(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "spent on your bobcard" in low or ("bobcard" in low and ("spent" in low or "is spent" in low)):
            return TransactionType.CREDIT
        if "transferred from" in low or "dr." in low or "debited" in low: return TransactionType.EXPENSE
        if "cr." in low or "credited" in low or "deposited" in low: return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def extract_available_limit(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Available\s+credit\s+limit\s+is\s+Rs\.?\s*([\d,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_available_limit(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        kw = ["dr. from", "cr. to", "credited to a/c", "credited with inr", "deposited in cash", "transferred from", "is spent"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
