import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class CIBEgyptParser(BankParser):
    """
    Parser for CIB (Commercial International Bank) Egypt SMS messages.
    """

    def get_bank_name(self) -> str:
        return "CIB Egypt"

    def get_currency(self) -> str:
        return "EGP"

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        if not self.is_transaction_message(sms_body):
            return None

        amount = self.extract_amount(sms_body)
        if amount is None:
            return None

        type = self.extract_transaction_type(sms_body)
        if type is None:
            return None

        currency = self.extract_currency(sms_body) or self.get_currency()

        return ParsedTransaction(
            amount=amount,
            type=type,
            merchant=self.extract_merchant(sms_body, sender),
            reference=self.extract_reference(sms_body),
            accountLast4=self.extract_account_last4(sms_body),
            balance=self.extract_balance(sms_body),
            creditLimit=self.extract_available_limit(sms_body),
            smsBody=sms_body,
            sender=sender,
            timestamp=timestamp,
            bankName=self.get_bank_name(),
            isFromCard=self.detect_is_card(sms_body),
            currency=currency
        )

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return norm == "CIB" or "CIB" in norm or re.match(r"^[A-Z]{2}-CIB(-[A-Z])?$", norm)

    def is_transaction_message(self, message: str) -> bool:
        lower = message.lower()
        if any(kw in lower for kw in ["otp", "one time password", "verification code"]):
            return False
        
        kw = ["was charged", "was debited", "was spent", "has been refunded", "credited"]
        return any(k in lower for k in kw)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        lower = message.lower()
        if "refunded" in lower: return TransactionType.INCOME
        if any(kw in lower for kw in ["was charged", "was debited", "was spent"]): return TransactionType.EXPENSE
        if "credited" in lower: return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        match = re.search(r"(?:for|with)\s+([A-Z]{3})\s+([0-9,]*\.?\d+)", message, re.IGNORE_CASE)
        if match:
            try: return Decimal(match.group(2).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_currency(self, message: str) -> Optional[str]:
        match = re.search(r"(?:for|with)\s+([A-Z]{3})\s+[0-9,]*\.?\d+", message, re.IGNORE_CASE)
        if match: return match.group(1).upper()
        return super().extract_currency(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        match = re.search(r"(?:credit\s+card|card)\s*(?:ending\s+with)?#(\d{4})", message, re.IGNORE_CASE)
        if match: return match.group(1)
        return super().extract_account_last4(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        lower = message.lower()
        if any(kw in lower for kw in ["was charged", "was debited", "was spent"]):
            m = re.search(r"at\s+([A-Z0-9\s\/&\-]+?)\s+on\s+\d", message, re.IGNORE_CASE)
            if m:
                merch = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(merch): return merch
        
        if "refunded" in lower:
            m = re.search(r"from\s+([A-Z0-9\s\/&\-]+?)\s+with\s+[A-Z]{3}", message, re.IGNORE_CASE)
            if m:
                merch = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(merch): return merch
        
        return super().extract_merchant(message, sender)

    def extract_available_limit(self, message: str) -> Optional[Decimal]:
        match = re.search(r"(?:Card\s+)?available\s+limit\s+is\s+[A-Z]{3}\s+([0-9,]+(?:\.\d{2})?)", message, re.IGNORE_CASE)
        if match:
            try: return Decimal(match.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_available_limit(message)

    def detect_is_card(self, message: str) -> bool:
        lower = message.lower()
        return any(kw in lower for kw in ["credit card", "debit card", "card ending", "card#"])
