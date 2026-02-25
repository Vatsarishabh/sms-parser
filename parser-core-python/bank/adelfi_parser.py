import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class AdelFiParser(BankParser):
    """
    Parser for AdelFi Credit Union transactions.
    """

    def get_bank_name(self) -> str:
        return "AdelFi"

    def get_currency(self) -> str:
        return "USD"

    def can_handle(self, sender: str) -> bool:
        return "42141" in sender

    def is_transaction_message(self, message: str) -> bool:
        return "Transaction Alert from AdelFi" in message and "had a transaction of" in message

    def extract_amount(self, message: str) -> Optional[Decimal]:
        match = re.search(r"\(\$(\d+(?:\.\d{2})?)\)", message)
        if match:
            try: return Decimal(match.group(1))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        match = re.search(r"Description:\s*(.+?)(?:\.\s*Date:|$)", message, re.IGNORE_CASE)
        if match:
            desc = match.group(1).strip()
            if desc:
                cleaned = re.sub(r"^\d+\s+", "", desc).strip()
                return self.clean_merchant_name(cleaned)
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        match = re.search(r"\*\*(\d{4})", message)
        return match.group(1) if match else None

    def extract_transaction_type(self, message: str) -> TransactionType:
        return TransactionType.CREDIT
