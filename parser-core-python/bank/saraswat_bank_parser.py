import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class SaraswatBankParser(BaseIndianBankParser):
    """
    Parser for Saraswat Co-operative Bank.
    """

    def get_bank_name(self) -> str:
        return "Saraswat Co-operative Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if up in ["SARBNK", "SARASWAT", "SARASWATBANK"]: return True
        pats = [r"^[A-Z]{2}-SARBNK-[ST]$", r"^[A-Z]{2}-SARASWAT-[ST]$", r"^[A-Z]{2}-SARBNK$", r"^[A-Z]{2}-SARASWAT$"]
        return any(re.match(p, up) for p in pats)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"INR\s+(\d+(?:,\d{3})*(?:\.\d{2})?)", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        m2 = re.search(r"Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "is credited" in low or "credited with" in low: return TransactionType.INCOME
        if "is debited" in low or "debited with" in low or "withdrawn" in low: return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"towards\s+(.+?)(?:\.\s*Current|\s*Current|$)", message, re.I)
        if m1:
            mer = m1.group(1).strip()
            mer = re.sub(r"^ACH\s+Credit:\s*", "", mer, flags=re.I)
            mer = re.sub(r"^ACH\s+Debit:\s*", "", mer, flags=re.I).strip()
            if self.is_valid_merchant_name(mer): return self.clean_merchant_name(mer)
            
        m2 = re.search(r"for\s+([A-Z.]+?)(?:\.\s+Current|\s+Current|$)", message, re.I)
        if m2:
            mer = m2.group(1).strip().rstrip(".")
            up = mer.upper()
            if up in ["S.I", "SI"]: return "Standing Instruction"
            if up == "NEFT": return "NEFT Transfer"
            if up == "RTGS": return "RTGS Transfer"
            if up == "IMPS": return "IMPS Transfer"
            return mer
            
        low = message.lower()
        if "atm" in low or "withdrawn" in low: return "ATM Withdrawal"
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"A/c\s+no\.\s+(?:ending\s+with\s+)?(\d{4,6})", message, re.I)
        if m1: return m1.group(1)[-4:]
        m2 = re.search(r"account\s+no\.\s+ending\s+with\s+(\d{4,6})", message, re.I)
        if m2: return m2.group(1)[-4:]
        m3 = re.search(r"A/c\s+\*(\d{4})", message, re.I)
        if m3: return m3.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"Current\s+Bal\s+is\s+INR\s+(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:CR|DR)?", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        m2 = re.search(r"Bal[:\s]+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "one time password", "verification code"]): return False
        kw = ["is credited with", "is debited with", "credited with inr", "debited with inr", "current bal is"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
