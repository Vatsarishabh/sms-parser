import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class LazyPayParser(BankParser):
    """
    Parser for LazyPay wallet transactions.
    """

    def get_bank_name(self) -> str:
        return "LazyPay"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "LZYPAY" in up or "LAZYPAY" in up

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"on\s+([^.]+?)\s+was\s+successful", message, re.I)
        if m:
            raw = m.group(1).strip()
            low = raw.lower()
            if "zepto marketplace" in low: return "Zepto"
            if "innovative retail concepts" in low: return "BigBasket"
            if "swiggy" in low: return "Swiggy"
            if "zomato" in low: return "Zomato"
            
            cleaned = re.sub(r"\s*(Private|Pvt\.?|Ltd\.?|Limited|Inc\.?|LLC|LLP).*$", "", raw, flags=re.I)
            cleaned = re.sub(r"\s*\d+$", "", cleaned).strip()
            if cleaned: return cleaned
            
        if "against your lazypay statement" in message.lower(): return "LazyPay Repayment"
        return super().extract_merchant(message, sender) or "LazyPay"

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Rs\.?\s*([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"txn\s+([A-Z0-9]+)", message, re.I)
        return m.group(1).strip() if m else super().extract_reference(message)

    def extract_transaction_type(self, message: str) -> TransactionType:
        return TransactionType.CREDIT

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["could not be processed", "due to a failure", "payment failed", "transaction failed", "unsuccessful"]):
            return False
        if any(k in low for k in ["offer", "get cashback", "explore more"]):
            if "payment of" not in low and "was successful" not in low: return False
        kw = ["payment of", "was successful", "against your lazypay statement", "thanks for your payment"]
        return any(k in low for k in kw)
