import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class DBSBankParser(BankParser):
    """
    Parser for DBS Bank (Development Bank of Singapore) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "DBS Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return any(k in norm for k in ["DBSBNK", "DBS", "DBSBANK"]) or \
               re.match(r"^[A-Z]{2}-(DBSBNK|DBS|DBSBANK)-[ST]$", norm)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [re.compile(r"(?:debited|credited)\s+with\s+INR\s*([0-9,]+(?:\.\d{2})?)", re.I),
                re.compile(r"INR\s*([0-9,]+(?:\.\d{2})?)\s+(?:debited|credited)", re.I)]
        for p in pats:
            m = p.search(message)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"account\s+no\s+\*+(\d{4})", r"a/c\s+\*+(\d{4})", r"account\s+\*+(\d{4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [re.compile(r"Current\s+Balance\s+is\s+INR\s*([0-9,]+(?:\.\d{2})?)", re.I),
                re.compile(r"Balance[:\s]+INR\s*([0-9,]+(?:\.\d{2})?)", re.I),
                re.compile(r"Avl\s+Bal[:\s]+INR\s*([0-9,]+(?:\.\d{2})?)", re.I)]
        for p in pats:
            m = p.search(message)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "debited" in low or "withdrawn" in low: return TransactionType.EXPENSE
        if "credited" in low or "deposited" in low: return TransactionType.INCOME
        return super().extract_transaction_type(message)
