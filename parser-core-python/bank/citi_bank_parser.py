import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class CitiBankParser(BankParser):
    """
    Parser for Citi Bank (USA) - handles USD credit card transactions.
    """

    def get_bank_name(self) -> str:
        return "Citi Bank"

    def get_currency(self) -> str:
        return "USD"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "CITI" or "CITIBANK" in up or up == "692484" or re.match(r"^[A-Z]{2}-CITI-[A-Z]$", up)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"\$([0-9,]+(?:\.[0-9]{2})?)\s+transaction",
                r"transaction.*?\$([0-9,]+(?:\.[0-9]{2})?)",
                r"A\s+\$([0-9,]+(?:\.[0-9]{2})?)\s+transaction"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(kw in low for kw in ["transaction was made", "card ending", "was not present", "transaction"]):
            return TransactionType.EXPENSE
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"transaction was made at\s+([^.]+?)(?:\s+on|$)", message, re.I)
        if m: return self.clean_merchant_name(m.group(1).strip())
        
        m = re.search(r"transaction at\s+([^.]+?)(?:\s+View|\.|$)", message, re.I)
        if m: return self.clean_merchant_name(m.group(1).strip())
        
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"card ending in\s+(\d{4})", message, re.I)
        if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"on\s+(card ending|\w+\s+\d{1,2},\s+\d{4})", message, re.I)
        if m and "card ending" not in m.group(1): return m.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        kw = ["citi alert:", "transaction was made", "card ending", "was not present for", "view details at citi.com"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
