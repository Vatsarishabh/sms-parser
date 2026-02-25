import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class AirtelPaymentsBankParser(BankParser):
    """
    Parser for Airtel Payments Bank SMS messages
    """

    def get_bank_name(self) -> str:
        return "Airtel Payments Bank"

    def can_handle(self, sender: str) -> bool:
        return "AIRBNK" in sender.upper()

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [
            r"credited\s+with\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
            r"Rs\.?\s*([0-9,]+(?:\.\d{2})?)\s+debited\s+from",
            r"debited\s+with\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"
        ]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(k in low for k in ["credited with", "is credited", "credit"]): return TransactionType.INCOME
        if any(k in low for k in ["debited from", "debited with", "debit"]): return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        if "airtel payments bank" in message.lower(): return "Airtel Payments Bank Transaction"
        sup = super().extract_merchant(message, sender)
        return sup if sup else "Airtel Payments Bank"

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"Txn\s+ID[:\s]+([A-Z0-9]+)", r"Transaction\s+ID[:\s]+([A-Z0-9]+)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                tid = m.group(1)
                if "x" not in tid.lower(): return tid
        return super().extract_reference(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Bal[:\s]+([0-9,]+(?:\.\d{2})?)", r"Balance[:\s]+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "verification", "request", "failed"]): return False
        if "credited with" in low or "debited from" in low or ("airtel payments bank" in low and ("credited" in low or "debited" in low)):
            return True
        return super().is_transaction_message(message)
