import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class LaxmiBankParser(BankParser):
    """
    Parser for Laxmi Sunrise Bank (Nepal) - handles NPR currency transactions.
    """

    def get_bank_name(self) -> str:
        return "Laxmi Sunrise Bank"

    def get_currency(self) -> str:
        return "NPR"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "LAXMI_ALERT" or "LAXMI" in up or "LAXMISUNRISE" in up or bool(re.match(r"^[A-Z]{2}-LAXMI-[A-Z]$", up))

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"NPR\s+([0-9,]+(?:\.[0-9]{2})?)\s",
                r"NPR\s+([0-9,]+(?:\.[0-9]{2})?)(?:\s|$)",
                r"(?:debited|credited)\s+by\s+NPR\s+([0-9,]+(?:\.[0-9]{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "has been debited" in low or "debited by" in low: return TransactionType.EXPENSE
        if "has been credited" in low or "credited by" in low: return TransactionType.INCOME
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"Remarks:\s*\(?([^)]+)\)?", message, re.I)
        if m:
            rem = m.group(1).strip()
            if "ESEWA LOAD" in rem.upper(): return "ESEWA"
            if "STIPEND PMT" in rem.upper(): return "Stipend Payment"
            if "/" in rem: rem = rem.split("/")[0].strip()
            return self.clean_merchant_name(rem)
            
        if "esewa" in message.lower(): return "ESEWA"
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"Your\s+#(\d+)\s+has\s+been", message, re.I)
        if m:
            acc = m.group(1)
            return acc[-4:] if len(acc) > 4 else acc
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"on\s+(\d{2}/\d{2}/\d{2})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"Remarks:.*?([0-9]{6,})", message, re.I)
        if m2: return m2.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        kw = ["dear customer", "has been debited", "has been credited", "laxmi sunrise", "remarks:", "npr"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
