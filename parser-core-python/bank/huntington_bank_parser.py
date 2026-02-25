import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class HuntingtonBankParser(BankParser):
    """
    Parser for Huntington Bank SMS messages (USA).
    """

    def get_bank_name(self) -> str:
        return "Huntington Bank"

    def get_currency(self) -> str:
        return "USD"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "HUNTINGTON" in up or up == "HUNTINGTON BANK" or bool(re.match(r"^[A-Z]{2}-HUNTINGTON-[A-Z]$", up))

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"withdrawal:\s+\$([0-9,]+(?:\.\d{2})?)\s+at", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(k in low for k in ["withdrawal", "debit card withdrawal", "atm withdrawal", "ach withdrawal"]):
            return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"at\s+(.+?)\.\s+Acct", message, re.I)
        if m:
            mer = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"Acct\s+CK(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"account\s+ending\s+(\d{4})", message, re.I)
        if m2: return m2.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"has\s+a\s+(-?\$[0-9,]+(?:\.\d{2})?)\s+bal", message, re.I)
        if m:
            bal_str = m.group(1).replace("$", "").replace(",", "")
            try: return Decimal(bal_str)
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "heads up" in low and "withdrawal" not in low: return False
        kw = ["we processed a debit card withdrawal", "we processed an atm withdrawal", "we processed an ach withdrawal"]
        return any(k in low for k in kw) or super().is_transaction_message(message)

    def detect_is_card(self, message: str) -> bool:
        low = message.lower()
        if "debit card withdrawal" in low or "atm withdrawal" in low: return True
        if "ach withdrawal" in low: return False
        return super().detect_is_card(message)
