import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class AUBankParser(BaseIndianBankParser):
    """
    Parser for AU Small Finance Bank SMS messages
    """

    def get_bank_name(self) -> str:
        return "AU Small Finance Bank"

    def can_handle(self, sender: str) -> bool:
        return "AUBANK" in sender.upper()

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [
            r"Credited\s+INR\s+([0-9,]+(?:\.\d{2})?)\s+to",
            r"Debited\s+INR\s+([0-9,]+(?:\.\d{2})?)\s+from",
            r"INR\s+([0-9,]+(?:\.\d{2})?)\s+spent",
            r"withdrawn\s+INR\s+([0-9,]+(?:\.\d{2})?)"
        ]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"Ref\s+UPI/[^/]+/[^/]+/[^/]+\s+([^(]+)\([^)]+\)", message, re.I)
        if m1:
            mer = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer

        m2 = re.search(r"UPI/[^/]+/[^/]+/[^/]+\s+[^(]*\(([^)]+)\)", message, re.I)
        if m2:
            mer = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer

        if "ATM" in message.upper() or "withdrawn" in message.lower():
            return "ATM Withdrawal"

        m3 = re.search(r"(?:to|from)\s+([^.\n]+?)(?:\.\s*|$)", message, re.I)
        if m3:
            mer = self.clean_merchant_name(m3.group(1).strip())
            if self.is_valid_merchant_name(mer) and "A/c" not in mer: return mer

        return super().extract_merchant(message, sender)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(k in low for k in ["credited", "received", "deposited", "refund"]): return TransactionType.INCOME
        if any(k in low for k in ["debited", "withdrawn", "spent", "paid"]): return TransactionType.EXPENSE
        if "credit card" in low and "spent" in low: return TransactionType.CREDIT
        return super().extract_transaction_type(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"A/c\s+(\d+)", message, re.I)
        if m:
            acc = m.group(1)
            return acc[-4:] if len(acc) >= 4 else acc
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Bal\s+INR\s+([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "one time password", "verification code"]): return False
        kw = ["credited inr", "debited inr", "withdrawn inr", "bal inr", "ref upi"]
        if any(k in low for k in kw): return True
        return super().is_transaction_message(message)
