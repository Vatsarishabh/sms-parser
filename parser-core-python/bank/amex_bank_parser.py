import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType
from parsed_transaction import ParsedTransaction

class AMEXBankParser(BankParser):
    """
    Parser for American Express (AMEX) card SMS messages
    """

    def get_bank_name(self) -> str:
        return "American Express"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if "AMEX" in up or "AMEXIN" in up: return True
        pats = [r"^[A-Z]{2}-AMEXIN-S$", r"^[A-Z]{2}-AMEX-S$", r"^[A-Z]{2}-AMEXIN-[TPG]$", r"^[A-Z]{2}-AMEX-[TPG]$", r"^[A-Z]{2}-AMEXIN$", r"^[A-Z]{2}-AMEX$"]
        return any(re.match(p, up) for p in pats)

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        parsed = super().parse(sms_body, sender, timestamp)
        if parsed:
            parsed.type = TransactionType.CREDIT
        return parsed

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"spent\s+INR\s+([0-9,]+(?:\.\d{2})?)\s+on", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        
        m2 = re.search(r"INR\s+([0-9,]+(?:\.\d{2})?)\s+spent", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"at\s+([^•\n]+?)\s+on\s+\d{1,2}\s+\w+", message, re.I)
        if m:
            mer = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"AMEX\s+card\s+\*+\s*(\d+)", message, re.I)
        if m1:
            c = m1.group(1)
            return c[-4:] if len(c) >= 4 else c
        
        m2 = re.search(r"card\s+ending\s+(\d{4})", message, re.I)
        if m2: return m2.group(1)
        
        return super().extract_account_last4(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["offer", "reward", "membership", "statement", "due date"]): return False
        return super().is_transaction_message(message)
