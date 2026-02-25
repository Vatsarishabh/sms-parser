import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from uae_bank_parser import UAEBankParser
from transaction_type import TransactionType

class LivBankParser(UAEBankParser):
    """
    Parser for Liv Bank (UAE) - Digital bank.
    """

    def get_bank_name(self) -> str:
        return "Liv Bank"

    def can_handle(self, sender: str) -> bool:
        norm = re.sub(r"\s+", "", sender.upper())
        return norm == "LIV" or "LIV" in norm or bool(re.match(r"^[A-Z]{2}-LIV-[A-Z]$", norm))

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "one time password", "verification code", "do not share", "activation", "has been blocked", "has been activated", "failed", "declined", "insufficient balance"]):
            return False
        kw = ["has been credited", "purchase of", "debit card ending", "credit card ending"]
        if any(k in low for k in kw): return True
        return super().is_transaction_message(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "purchase of" in low:
            m1 = re.search(r"at\s+([^,]+?)(?:,|\s+Avl|\.\s)", message, re.I)
            if m1:
                mer = m1.group(1).strip()
                if mer and "Avl Balance" not in mer: return self.clean_merchant_name(mer)
            m2 = re.search(r"at\s+([^.]+?)(?:\s+Avl|,)", message, re.I)
            if m2:
                mer = m2.group(1).strip()
                if mer: return self.clean_merchant_name(mer)
        if "has been credited" in low: return "Account Credit"
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"(?:Debit|Credit)\s+Card ending\s+(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"account\s+[0-9X]+([0-9A-Z]{2,4})", message, re.I)
        if m2:
            last = m2.group(1).replace("X", "").replace("x", "")
            if last: return last[-4:]
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Current balance is\s+([A-Z]{3})\s+([\d,]+(?:\.\d{2})?)",
                r"Avl Balance is\s+([A-Z]{3})\s+([\d,]+(?:\.\d{2})?)",
                r"Balance:?\s+([A-Z]{3})\s+([\d,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(2).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(k in low for k in ["has been credited", "credited to account", "refund", "cashback"]): return TransactionType.INCOME
        if any(k in low for k in ["purchase of", "debited", "withdrawn"]): return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def detect_is_card(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["debit card ending", "credit card ending", "purchase of"]): return True
        return super().detect_is_card(message)

    def contains_card_purchase(self, message: str) -> bool:
        low = message.lower()
        if "purchase of" in low and ("debit card ending" in low or "credit card ending" in low): return True
        return super().contains_card_purchase(message)

    def extract_currency(self, message: str) -> Optional[str]:
        pats = [r"purchase of\s+([A-Z]{3})\s+[\d,]+(?:\.\d{2})?",
                r"([A-Z]{3})\s+[\d,]+(?:\.\d{2})?[\s\n]+has been credited",
                r"([A-Z]{3})\s+[\d,]+(?:\.\d{2})?"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                cur = m.group(1).upper()
                if re.match(r"^[A-Z]{3}$", cur) and not re.match(r"^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$", cur, re.I):
                    return cur
        return "AED"
