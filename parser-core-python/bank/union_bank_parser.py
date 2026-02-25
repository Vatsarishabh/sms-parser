import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from .base_indian_bank_parser import BaseIndianBankParser

class UnionBankParser(BaseIndianBankParser):
    """
    Parser for Union Bank of India SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Union Bank of India"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if any(k in up for k in ["UNIONB", "UNIONBANK", "UBOI"]): return True
        pats = [r"^[A-Z]{2}-UNIONB-[ST]$", r"^[A-Z]{2}-UNIONB-[TPG]$", r"^[A-Z]{2}-UNIONB$", r"^[A-Z]{2}-UNIONBANK$"]
        return any(re.match(p, up) for p in pats)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        keys = ["debited", "credited", "withdrawn", "deposited", "spent", "received", "transferred", "paid"]
        if any(k in low for k in keys): return True
        return super().is_transaction_message(message)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"Rs[:.]?\s*([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        m2 = re.search(r"INR\s+([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        if "Mob Bk" in message: return "Mobile Banking Transfer"
        
        if "ATM" in message.upper():
            m = re.search(r"at\s+([^.\s]+(?:\s+[^.\s]+)*)(?:\s+on|\s+Avl|$)", message, re.I)
            if m: return self.clean_merchant_name(m.group(1).strip())
            return "ATM Withdrawal"
            
        if "UPI" in message.upper():
            m = re.search(r"UPI[/:]?\s*([^,.\s]+)", message, re.I)
            if m: return self.clean_merchant_name(m.group(1).strip())
            
        if "VPA" in message.upper():
            m = re.search(r"VPA\s+([^@\s]+)", message, re.I)
            if m: return self.parse_upi_merchant(m.group(1).strip())
            
        m_to = re.search(r"to\s+([^.\n]+?)(?:\s+on|\s+Avl|$)", message, re.I)
        if m_to and "Avl" not in m_to.group(1): return self.clean_merchant_name(m_to.group(1).strip())
        
        m_from = re.search(r"from\s+([^.\n]+?)(?:\s+on|\s+Avl|$)", message, re.I)
        if m_from and "Avl" not in m_from.group(1): return self.clean_merchant_name(m_from.group(1).strip())
        
        return super().extract_merchant(message, sender)

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"ref\s+no\s+([\w]+)", r"ref[:#]?\s*([\w]+)", r"reference[:#]?\s*([\w]+)", r"txn[:#]?\s*([\w]+)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1).strip()
        return super().extract_reference(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"A/[Cc]\s*[*X](\d{4})", r"Account\s*[*X](\d{4})", r"Acc\s*[*X](\d{4})", r"A/[Cc]\s+(\d{4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Avl\s+Bal\s+Rs[:.]?\s*([0-9,]+(?:\.\d{2})?)",
                r"Available\s+Balance[:.]?\s*Rs[:.]?\s*([0-9,]+(?:\.\d{2})?)",
                r"Balance[:.]?\s*Rs[:.]?\s*([0-9,]+(?:\.\d{2})?)",
                r"Bal[:.]?\s*Rs[:.]?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def parse_upi_merchant(self, vpa: str) -> str:
        low = vpa.lower()
        if "paytm" in low: return "Paytm"
        if "phonepe" in low: return "PhonePe"
        if "googlepay" in low or "gpay" in low: return "Google Pay"
        if "bharatpe" in low: return "BharatPe"
        if "amazon" in low: return "Amazon"
        if "flipkart" in low: return "Flipkart"
        if "swiggy" in low: return "Swiggy"
        if "zomato" in low: return "Zomato"
        if "uber" in low: return "Uber"
        if "ola" in low: return "Ola"
        if vpa.isdigit(): return "Individual"
        parts = re.split(r"[.\-_]", low)
        for pt in parts:
            if len(pt) > 3 and not pt.isdigit(): return pt.capitalize()
        return "Merchant"
