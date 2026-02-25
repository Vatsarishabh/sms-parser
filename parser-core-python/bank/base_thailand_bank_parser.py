import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Set

from bank_parser import BankParser
from transaction_type import TransactionType

class BaseThailandBankParser(BankParser):
    """
    Base class for Thai bank parsers to share common logic.
    Handles both Thai and English language transaction patterns with THB currency.
    """

    def get_currency(self) -> str:
        return "THB"

    def extract_amount(self, message: str) -> Optional[Decimal]:
        # Pattern 1: "1,250.00 THB" or "1,250.00 บาท"
        patterns = [
            r"([0-9,]+(?:\.[0-9]{1,2})?)\s*(?:THB|บาท)",
            r"(?:THB|฿)\s*([0-9,]+(?:\.[0-9]{1,2})?)",
            # Pattern 3: "1,250.00 USD" for international transactions
            r"([0-9,]+(?:\.[0-9]{1,2})?)\s*USD"
        ]

        for p in patterns:
            m = re.search(p, message, re.I)
            if m:
                try:
                    return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError):
                    pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()

        if self.is_investment_transaction(low):
            return TransactionType.INVESTMENT

        # Credit card spending
        if any(k in low for k in ["credit card spending", "ยอดใช้จ่ายต่างประเทศ", "ยอดใช้จ่าย"]):
            return TransactionType.CREDIT

        # Thai expense keywords
        expense_keys = ["เงินออก", "ถอนเงิน", "ถอนเงินสด", "โอนเงินออก", "โอนเงินผ่าน", "ใช้จ่ายบัตร", "ใช้จ่าย",
                        "withdrawal", "payment", "you spent", "transfer out", "card payment", "card transaction", "atm withdrawal"]
        if any(k in low for k in expense_keys):
            return TransactionType.EXPENSE

        # Thai income keywords
        income_keys = ["เงินเข้า", "เงินฝาก", "รับเงิน", "โอนเงินเข้า", "รับเงินพร้อมเพย์", "รับเงินโอน", "เงินฝากเข้า",
                       "deposit", "receive", "transfer in", "transfer received"]
        if any(k in low for k in income_keys):
            return TransactionType.INCOME

        return None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        # Thai: "คงเหลือ 15,820.45 บาท" or English: "Bal 15,820.45 THB"
        patterns = [
            r"(?:Bal|คงเหลือ)\s+([0-9,]+(?:\.[0-9]{1,2})?)\s*(?:THB|บาท)",
            r"(?:Bal|คงเหลือ)\s+([0-9,]+(?:\.[0-9]{1,2})?)"
        ]

        for p in patterns:
            m = re.search(p, message, re.I)
            if m:
                try:
                    return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError):
                    pass
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        # Pattern: "A/C xNNNN" or "บช xNNNN"
        m = re.search(r"(?:A/C|บช)\s*x(\d{4})", message, re.I)
        return m.group(1) if m else None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        # Thai: "ร้าน MERCHANT" or English: "at MERCHANT"
        patterns = [
            r"(?:at|ร้าน)\s+([A-Za-z0-9\s&._-]+?)(?:\s+(?:A/C|บช|Bal|คงเหลือ|Available|on|$))",
            r"(?:at|ร้าน)\s+([A-Za-z0-9\s&._-]+)$"
        ]

        for p in patterns:
            m = re.search(p, message, re.I)
            if m:
                mer = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(mer):
                    return mer
        return None

    def extract_available_limit(self, message: str) -> Optional[Decimal]:
        m = re.search(r"(?:Available limit|วงเงินคงเหลือ)\s+([0-9,]+(?:\.[0-9]{1,2})?)\s*(?:THB|บาท)", message, re.I)
        if m:
            try:
                return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError):
                pass
        return None

    def is_credit_card_message(self, message: str) -> bool:
        low = message.lower()
        card_keywords = [
            "credit card", "บัตรเครดิต",
            "card spending", "card payment", "card transaction",
            "ใช้จ่ายบัตร", "ยอดใช้จ่าย"
        ]
        return any(k in low for k in card_keywords)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()

        # Skip OTP messages
        if any(k in low for k in ["otp", "รหัส", "ยืนยัน"]):
            return False

        # Skip promotional messages
        if any(k in low for k in ["สมัคร", "โปรโมชั่น", "promotion", "cashback offer"]):
            return False

        transaction_keywords = [
            # Thai
            "เงินเข้า", "เงินออก", "ถอนเงิน", "โอนเงิน", "ใช้จ่าย",
            "เงินฝาก", "รับเงิน", "คงเหลือ", "บาท", "ยอดใช้จ่าย",
            # English
            "withdrawal", "deposit", "transfer", "payment", "spent",
            "receive", "bal", "thb", "card transaction", "card payment",
            "credit card spending", "available limit"
        ]
        return any(k in low for k in transaction_keywords)

    def clean_merchant_name(self, merchant: str) -> str:
        return merchant.strip()

    def is_valid_merchant_name(self, name: str) -> bool:
        common_words = {
            "USING", "VIA", "THROUGH", "BY", "WITH", "FOR", "TO", "FROM", "AT", "THE",
            "ผ่าน", "โดย", "จาก", "ที่", "ไปยัง", "ถึง"
        }

        if len(name) < 2: return False
        if not any(c.isalpha() for c in name): return False
        if name.upper() in common_words: return False
        if name.isdigit(): return False
        if "@" in name: return False
        return True
