import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class UCOBankParser(BankParser):
    """
    Parser for UCO Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "UCO Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if any(k in up for k in ["UCOBNK", "UCOBANK", "UCO BANK"]): return True
        pats = [r"^[A-Z]{2}-UCOBNK-[ST]$", r"^[A-Z]{2}-UCOBNK$", r"^[A-Z]{2}-UCOBANK$"]
        return any(re.match(p, up) for p in pats)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Rs\.?\s*([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "debited with" in low: return TransactionType.EXPENSE
        if "credited with" in low: return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"by\s+([^.]+?)(?:\.Avl|$)", message, re.I)
        if m:
            mer = m.group(1).strip()
            if "UCO-UPI" in mer.upper(): return "UPI Transfer"
            return self.clean_merchant_name(mer)
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"A/c\s+[X]{2}(\d{4})", r"Account\s+[X]{2}(\d{4})", r"Acc\s+[X]{2}(\d{4})", r"A/c\s+[*]{2}(\d{4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Avl\s+Bal\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Available\s+Balance\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Balance[:.]?\s*Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"ref[:#]?\s*([\w]+)", r"txn[:#]?\s*([\w]+)", r"transaction\s+id[:#]?\s*([\w]+)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1).strip()
        return super().extract_reference(message)
