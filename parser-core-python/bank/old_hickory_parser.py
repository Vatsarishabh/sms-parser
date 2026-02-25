import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class OldHickoryParser(BankParser):
    """
    Parser for Old Hickory Credit Union (USA) - handles USD currency transactions.
    """

    def get_bank_name(self) -> str:
        return "Old Hickory Credit Union"

    def get_currency(self) -> str:
        return "USD"

    def can_handle(self, sender: str) -> bool:
        clean = re.sub(r"[^\d]", "", sender)
        if clean == "8775907589": return True
        up = sender.upper()
        if up in ["OLDHICKORY", "OHCU"] or "HICKORY" in up or "OLD HICKORY" in up: return True
        return bool(re.match(r"^[A-Z]{2}-HICKORY-[A-Z]$", up))

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"\$([0-9,]+(?:\.[0-9]{2})?)",
                r"transaction for\s+\$([0-9,]+(?:\.[0-9]{2})?)",
                r"posted.*?\$([0-9,]+(?:\.[0-9]{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if ("transaction" in low and "posted" in low) or "has posted" in low or "transaction for" in low:
            return TransactionType.EXPENSE
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"posted to\s+([^(]+)", message, re.I)
        if m:
            nm = m.group(1).strip()
            if nm: return f"Account: {self.clean_merchant_name(nm)}"
        return "Transaction Alert"

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"\(part of\s+([^)]+)\)", message, re.I)
        if m:
            inf = m.group(1).strip()
            dm = re.search(r"(\d{4,})", inf)
            if dm:
                dg = dm.group(1)
                return dg[-4:]
            return inf
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"above the\s+\$([0-9,]+(?:\.[0-9]{2})?)\s+value you set", message, re.I)
        if m: return f"Alert threshold: ${m.group(1)}"
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        kw = ["transaction", "has posted", "posted to", "above the", "value you set", "account name"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
