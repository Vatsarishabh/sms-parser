import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class YesBankParser(BaseIndianBankParser):
    """
    Parser for Yes Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Yes Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if up in ["YESBNK", "YESBANK"]: return True
        pats = [r"^[A-Z]{2}-YESBNK-S$", r"^[A-Z]{2}-YESBNK$"]
        return any(re.match(p, up) for p in pats)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"INR\s+([0-9,]+(?:\.\d{2})?)\s+spent", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"@UPI_([^0-9]+?)(?:\s+\d{2}-\d{2}-\d{4})", message, re.I)
        if m1:
            mer = " ".join(m1.group(1).split()).strip()
            if mer: return mer
            
        m2 = re.search(r"@UPI_([A-Z\s]+)", message, re.I)
        if m2:
            mer = " ".join(m2.group(1).split()).strip()
            if mer and self.is_valid_merchant_name(mer): return mer
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"YES\s+BANK\s+Card\s+[X]*(\d+)", message, re.I)
        if m1:
            num = m1.group(1)
            return num[-4:] if len(num) >= 4 else num
            
        m2 = re.search(r"SMS\s+BLKCC\s+(\d{4})", message, re.I)
        if m2: return m2.group(1)
        
        return super().extract_account_last4(message)

    def extract_available_limit(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Avl\s+Lmt\s+INR\s+([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_available_limit(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if self.is_investment_transaction(low): return TransactionType.INVESTMENT
        if "spent" in low and "yes bank card" in low and "avl lmt" in low: return TransactionType.CREDIT
        if any(k in low for k in ["debited", "withdrawn", "spent", "charged", "paid"]): return TransactionType.EXPENSE
        if any(k in low for k in ["credited", "deposited", "received", "refund"]): return TransactionType.INCOME
        return None

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "verification", "one time password"]): return False
        if any(k in low for k in ["offer", "cashback offer", "discount"]): return False
        keys = ["spent on yes bank card", "debited", "credited", "withdrawn", "deposited", "avl lmt"]
        return any(k in low for k in keys) or super().is_transaction_message(message)

    def detect_is_card(self, message: str) -> bool:
        low = message.lower()
        if "yes bank card" in low or "sms blkcc" in low: return True
        return super().detect_is_card(message)
