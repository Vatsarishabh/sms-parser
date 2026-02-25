import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser

class KarnatakaBankParser(BankParser):
    """
    Parser for Karnataka Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Karnataka Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if any(k in up for k in ["KARNATAKA BANK", "KARNATAKABANK", "KBLBNK", "KTKBANK", "KARBANK"]): return True
        pats = [r"^[A-Z]{2}-KBLBNK-S$", r"^[A-Z]{2}-KARBANK-S$", r"^[A-Z]{2}-KBLBNK$"]
        return any(re.match(p, up) for p in pats) or up in ["KBLBNK", "KARBANK"]

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"DEBITED\s+for\s+Rs\.?([0-9,]+(?:\.\d{2})?)/?\-?", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        m2 = re.search(r"credited\s+by\s+Rs\.?([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"ACH[A-Za-z]*-([^/]+)/", message, re.I)
        if m1:
            mer = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m2 = re.search(r"from\s+([^\s]+)\s+on", message, re.I)
        if m2:
            mer = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        low = message.lower()
        if "lic of india" in low: return "LIC of India"
        if "upi" in low and not m2: return "UPI Transaction"
        
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"Account\s+[xX]*([0-9]{4,6})[xX]*", message, re.I)
        if m1:
            dig = m1.group(1)
            return dig[-4:] if len(dig) > 4 else dig
        m2 = re.search(r"a/c\s+[xX]{0,2}([0-9]{4,6})", message, re.I)
        if m2: return m2.group(1)[-4:]
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"UPI\s+Ref\s+no\s+([0-9]+)", message, re.I)
        return m.group(1) if m else super().extract_reference(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Balance\s+is\s+Rs\.?([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)
