import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class EquitasBankParser(BaseIndianBankParser):
    """
    Parser for Equitas Small Finance Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Equitas Small Finance Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return any(k in norm for k in ["EQUTAS", "EQUITA", "EQUITS"])

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"INR\s+([0-9,]+(?:\.\d{2})?)\s+(?:debited|credited)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "debited" in low or "withdrawn" in low: return TransactionType.EXPENSE
        if "credited" in low or "deposited" in low: return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "debited" in low:
            m = re.search(r"on\s+\d{2}-\d{2}-\d{2}\s+to\s+([^.]+?)(?:\.\s*Avl|\.\s*Not|\.Not|\.$)", message, re.I)
            if m:
                merch = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(merch): return merch
                
        if "credited" in low:
            m = re.search(r"on\s+\d{2}-\d{2}-\d{2}\s+from\s+([^.]+?)(?:\.\s*Avl|\.\s*Not|\.Not|\.$)", message, re.I)
            if m:
                merch = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(merch): return merch

        if "via upi" in low: return "UPI Transaction"
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"(?:Equitas\s+)?A/c\s+[X]*(\d{2,4})", message, re.I)
        if m:
            val = m.group(1)
            return val[-4:] if len(val) >= 4 else val
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Avl\s+Bal\s+is\s+INR\s+([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"-?Ref[:\s]*([A-Z0-9]+)", message, re.I)
        if m: return m.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(kw in low for kw in ["otp", "one time password", "verification code"]): return False
        if any(kw in low for kw in ["offer", "discount", "cashback offer"]): return False
        kw = ["debited", "credited", "withdrawn", "deposited", "transferred", "received", "paid"]
        return any(k in low for k in kw)
