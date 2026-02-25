import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class DiscoverCardParser(BankParser):
    """
    Parser for Discover Card - handles USD credit card transactions.
    """

    def get_bank_name(self) -> str:
        return "Discover Card"

    def get_currency(self) -> str:
        return "USD"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "DISCOVER" or "DISCOVERCARD" in up or up == "347268" or re.match(r"^[A-Z]{2}-DISCOVER-[A-Z]$", up)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"transaction of\s+\$([0-9,]+(?:\.[0-9]{2})?)",
                r"A transaction of\s+\$([0-9,]+(?:\.[0-9]{2})?)",
                r"\$([0-9,]+(?:\.[0-9]{2})?)\s+at"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(kw in low for kw in ["discover card alert", "transaction of", "transaction"]):
            return TransactionType.EXPENSE
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"at\s+([^\s]+(?:\s+[^\s]*)*?)(?:\s+on|\s+Text|$)", message, re.I)
        if m:
            merch = m.group(1).strip()
            if merch and not re.match(r"\w+\s+\d{1,2},\s+\d{4}", merch):
                return self.clean_merchant_name(merch)
        
        m = re.search(r"at\s+(PAYPAL\s+\*[^\s]+)", message, re.I)
        if m: return self.clean_merchant_name(m.group(1).strip())
        
        return super().extract_merchant(message, sender)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"on\s+(\w+\s+\d{1,2},\s+\d{4})", message, re.I)
        if m: return m.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "text stop to end" in low and "transaction of" not in low: return False
        kw = ["discover card alert:", "transaction of", "no action needed", "see it at https://app.discover.com"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
