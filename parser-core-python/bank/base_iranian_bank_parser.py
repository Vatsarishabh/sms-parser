import re
from decimal import Decimal, InvalidOperation
from typing import Optional, List

from bank_parser import BankParser
from transaction_type import TransactionType

class BaseIranianBankParser(BankParser):
    """
    Base class for Iranian bank parsers.
    """

    def get_currency(self) -> str:
        return "IRR"

    def extract_amount(self, message: str) -> Optional[Decimal]:
        patterns = [
            re.compile(r"مبلغ\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(?:ریال|تومان)"),
            re.compile(r"(\d{1,3}(?:,\d{3})*|\d+)\s*(?:ریال|تومان)")
        ]

        for pattern in patterns:
            match = pattern.search(message)
            if match:
                clean_amount = match.group(1).replace(",", "")
                try:
                    amount = Decimal(clean_amount)
                    return amount if amount >= 1000 else None
                except (InvalidOperation, ValueError):
                    pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        lower_message = message.lower()
        if self.is_investment_transaction(lower_message):
            return TransactionType.INVESTMENT

        expense_keywords = ["برداشت", "پرداخت", "خرید", "انتقال", "مصرف"]
        if any(kw in lower_message for kw in expense_keywords):
            return TransactionType.EXPENSE

        if "واریز" in lower_message or ("credited" in lower_message and "block" not in lower_message):
            return TransactionType.INCOME

        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        match = re.search(r"(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})", message)
        if match:
            return f"Card {match.group(1)}"
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        match = re.search(r"\d{4}[-\s]?(\d{4})", message)
        return match.group(1) if match else None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        match = re.search(r"مانده\s*:?\s*(\d{1,3}(?:,\d{3})*)", message)
        if match:
            try:
                return Decimal(match.group(1).replace(",", ""))
            except (InvalidOperation, ValueError):
                pass
        return None

    def detect_is_card(self, message: str) -> bool:
        keywords = ["کارت", "card", "debit card", "credit card", "کارت بدهی", "کارت اعتباری"]
        return any(kw in message.lower() for kw in keywords)

    def is_transaction_message(self, message: str) -> bool:
        lower_message = message.lower()
        if any(kw in lower_message for kw in ["otp", "رمز یکبار مصرف", "کد تایید"]):
            return False
        if any(kw in lower_message for kw in ["تبلیغ", "پیشنهاد", "تخفیف", "cashback offer"]):
            return False
        if "درخواست" in lower_message and "پرداخت" in lower_message:
            return False

        keywords = ["مبلغ", "ریال", "تومان", "IRR", "TOMAN", "برداشت", "واریز", "پرداخت", "خرید", "انتقال", "debit", "credit", "spent", "received", "transferred", "paid"]
        return any(kw in lower_message for kw in keywords)

    def is_valid_merchant_name(self, name: str) -> bool:
        common_words = {
            "USING", "VIA", "THROUGH", "BY", "WITH", "FOR", "TO", "FROM", "AT", "THE",
            "استفاده", "از", "توسط", "از طریق", "برای", "به", "در", "و", "با"
        }
        return (len(name) >= 2 and any(c.isalpha() for c in name) and
                name.upper() not in common_words and not name.isdigit() and "@" not in name)
