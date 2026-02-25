import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class OneCardParser(BankParser):
    """
    Parser for OneCard credit card SMS messages.
    """

    def get_bank_name(self) -> str:
        return "OneCard"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if "ONECRD" in up or "ONECARD" in up: return True
        pats = [r"^[A-Z]{2}-ONECRD-S$", r"^[A-Z]{2}-ONECARD-S$", r"^[A-Z]{2}-ONECRD-[TPG]$", r"^[A-Z]{2}-ONECARD-[TPG]$", r"^[A-Z]{2}-ONECRD$", r"^[A-Z]{2}-ONECARD$"]
        return any(re.match(p, up) for p in pats) or up in ["ONECRD", "ONECARD"]

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        parsed = super().parse(sms_body, sender, timestamp)
        if not parsed: return None
        parsed.type = TransactionType.CREDIT
        return parsed

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"for\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)\s+at",
                r"of\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)\s+on",
                r"spent\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"at\s+([^•\n]+?)\s+on\s+card", message, re.I)
        if m1 and self.is_valid_merchant_name(self.clean_merchant_name(m1.group(1).strip())):
            return self.clean_merchant_name(m1.group(1).strip())
            
        m2 = re.search(r"on\s+([^•\n]+?)\s+on\s+card", message, re.I)
        if m2 and self.is_valid_merchant_name(self.clean_merchant_name(m2.group(1).strip())):
            return self.clean_merchant_name(m2.group(1).strip())
            
        m3 = re.search(r"at\s+([^•\n]+?)\s+on", message, re.I)
        if m3 and self.is_valid_merchant_name(self.clean_merchant_name(m3.group(1).strip())):
            return self.clean_merchant_name(m3.group(1).strip())
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"card\s+ending\s+[X]*(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"on\s+card\s+[X]*(\d{4})", message, re.I)
        if m2: return m2.group(1)
        return super().extract_account_last4(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["offer", "cashback offer", "get reward", "statement", "due date", "bill generated"]):
            return False
        if low.startswith("you've") and "on card ending" in low: return True
        if "spent" in low or "made a" in low: return True
        return super().is_transaction_message(message)
