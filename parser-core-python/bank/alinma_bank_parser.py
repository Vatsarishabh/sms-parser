import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class AlinmaBankParser(BankParser):
    """
    Parser for Alinma Bank (Saudi Arabia) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Alinma Bank"

    def get_currency(self) -> str:
        return "SAR"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return "ALINMA" in norm or "الإنماء" in norm

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [re.compile(r"بمبلغ:\s*([0-9]+(?:\.[0-9]{2})?)\s*SAR", re.IGNORE_CASE),
                re.compile(r"مبلغ:\s*SAR\s*([0-9]+(?:\.[0-9]{2})?)", re.IGNORE_CASE),
                re.compile(r"مبلغ:\s*ريال سعودى\s*([0-9]+(?:\.[0-9]{2})?)")]
        for p in pats:
            m = p.search(message)
            if m:
                try: return Decimal(m.group(1))
                except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        if "شراء" in message or "purchase" in message.lower(): return TransactionType.EXPENSE
        if "إيداع" in message or "deposit" in message.lower(): return TransactionType.INCOME
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"من:\s*([^\n]+?)(?:\n|في:)", message, re.IGNORE_CASE)
        if m:
            merch = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
        
        m = re.search(r"لدى:\s*([^\n]+?)(?:\n|في:)", message, re.IGNORE_CASE)
        if m:
            merch = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch

        if "pos" in message.lower() or "نقاط البيع" in message: return "POS Transaction"
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"حساب:\s*\*+(\d{4})", r"حساب:\s*\*(\d{4})", r"البطاقة:\s*\*+(\d{4})", r"البطاقة الائتمانية:\s*\*+(\d{4})", r"بطاقة مدى:\s*(\d{4})\*"]
        for p in pats:
            m = re.search(p, message)
            if m: return m.group(1)
        return None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [re.compile(r"الرصيد:\s*([0-9]+(?:\.[0-9]{2})?)\s*SAR", re.IGNORE_CASE),
                re.compile(r"الرصيد:\s*([0-9]+(?:\.[0-9]{2})?)\s*ريال")]
        for p in pats:
            m = p.search(message)
            if m:
                try: return Decimal(m.group(1))
                except (InvalidOperation, ValueError): pass
        return None

    def is_transaction_message(self, message: str) -> bool:
        if any(kw in message.lower() or kw in message for kw in ["otp", "رمز", "كلمة المرور"]): return False
        kw = ["شراء", "بمبلغ", "مبلغ", "الرصيد", "Purchase", "POS"]
        return any(k in message or k in message.lower() for k in kw)

    def detect_is_card(self, message: str) -> bool:
        kw = ["البطاقة", "بطاقة", "البطاقة الائتمانية", "بطاقة مدى", "POS", "نقاط البيع"]
        return any(k in message for k in kw)
