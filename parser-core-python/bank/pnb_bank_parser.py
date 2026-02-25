import re
from decimal import Decimal, InvalidOperation
from typing import Optional
import unicodedata

from base_indian_bank_parser import BaseIndianBankParser
from parsed_transaction import ParsedTransaction

class PNBBankParser(BaseIndianBankParser):
    """
    Parser for Punjab National Bank (PNB) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Punjab National Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if "PUNJAB NATIONAL BANK" in up or "PNBBNK" in up or "PUNBN" in up: return True
        pats = [r"^[A-Z]{2}-PNBBNK-S$", r"^[A-Z]{2}-PNB-S$", r"^[A-Z]{2}-PNBBNK$", r"^[A-Z]{2}-PNB$"]
        return any(re.match(p, up) for p in pats) or up in ["PNBBNK", "PNB"]

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        norm = self.normalize_unicode_text(sms_body)
        return super().parse(norm, sender, timestamp)

    def normalize_unicode_text(self, text: str) -> str:
        # Compatibility Decomposition
        norm = unicodedata.normalize('NFKD', text)
        return "".join([c for c in norm if ord(c) < 128])

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"debited\s+(?:Rs\.?|INR)\s*([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        m2 = re.search(r"(?:(?:Rs\.?|INR)\s*([0-9,]+(?:\.\d{2})?)\s+(?:has\s+been\s+)?credited|credited\s+(?:Rs\.?|INR)\s*([0-9,]+(?:\.\d{2})?))", message, re.I)
        if m2:
            amt = m2.group(1) if m2.group(1) else m2.group(2)
            try: return Decimal(amt.replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"From\s+([^/]+)/", message, re.I)
        if m:
            mer = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
        low = message.lower()
        if "neft" in low: return "NEFT Transfer"
        if "upi" in low: return "UPI Transaction"
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"A/c\s+(?:XX|X\*+)?(\d{4})", message, re.I)
        return m.group(1) if m else super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"ref\s+no\.\s+([A-Z0-9]+)", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"UPI:\s*([0-9]+)", message, re.I)
        if m2: return m2.group(1)
        return super().extract_reference(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Bal\s+(?:INR\s+|Rs\.?)([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        if "register for e-statement" in message.lower(): return True
        return super().is_transaction_message(message)
