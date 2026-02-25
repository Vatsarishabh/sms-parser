import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class JuspayParser(BaseIndianBankParser):
    """
    Parser for Juspay/Amazon Pay wallet transactions.
    """

    def get_bank_name(self) -> str:
        return "Amazon Pay"

    def get_currency(self) -> str:
        return "INR"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "JUSPAY" in up or "APAY" in up or up == "AMAZON PAY"

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"debited\s+for\s+INR\s+([0-9,]+(?:\.[0-9]{1,2})?)",
                r"Payment\s+of\s+Rs\s+([0-9,]+(?:\.[0-9]{1,2})?)",
                r"Rs\s+([0-9,]+(?:\.[0-9]{1,2})?)",
                r"INR\s+([0-9,]+(?:\.[0-9]{1,2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"successful\s+at\s+(.+?)(?:\.\s*Updated|\s*\.\s*Updated|\.(?:\s|$))", message, re.I)
        if m: return m.group(1).strip()
        
        low = message.lower()
        if "amazon" in low: return "Amazon"
        if "flipkart" in low: return "Flipkart"
        if "swiggy" in low: return "Swiggy"
        if "zomato" in low: return "Zomato"
        if "ola" in low: return "Ola"
        if "uber" in low: return "Uber"
        if "zepto" in low: return "Zepto"
        if "blinkit" in low: return "Blinkit"
        if "apay wallet" in low or "wallet" in low: return "Amazon Pay Transaction"
        
        return super().extract_merchant(message, sender) or "Amazon Pay"

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(k in low for k in ["debited", "payment", "charged"]): return TransactionType.EXPENSE
        if any(k in low for k in ["credited", "refunded", "received"]): return TransactionType.CREDIT
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"Transaction\s+Reference\s+Number\s+is\s+(\d{12})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"Reference\s+(?:Number|No)[:\s]+(\d{12})", message, re.I)
        if m2: return m2.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        kw = ["debited for", "payment of rs", "using apay balance", "transaction reference number", "updated balance is"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
