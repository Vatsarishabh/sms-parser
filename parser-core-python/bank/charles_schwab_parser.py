import re
from decimal import Decimal, InvalidOperation
from typing import Optional
import enum

from bank_parser import BankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class CharlesSchwabParser(BankParser):
    """
    Parser for Charles Schwab Bank - handles USD debit card and ATM transactions.
    """

    def get_bank_name(self) -> str:
        return "Charles Schwab"

    def get_currency(self) -> str:
        return "USD"

    def extract_currency(self, message: str) -> Optional[str]:
        symbol_map = {
            "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY",
            "฿": "THB", "₩": "KRW", "$": "USD", "C$": "CAD",
            "A$": "AUD", "S$": "SGD", "ብር": "ETB"
        }
        for symbol, code in symbol_map.items():
            if symbol in message: return code

        m = re.search(r"A\s+([A-Z]{3})\s*[0-9,]+", message)
        if m: return m.group(1).upper()

        m = re.search(r"\b([A-Z]{3})\b", message)
        if m:
            # In a real environment, we'd validate the currency code here.
            # For simplicity, we'll return it if it looks like one.
            return m.group(1).upper()

        return super().extract_currency(message) or "USD"

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        if not self.is_transaction_message(sms_body): return None

        amount = self.extract_amount(sms_body)
        if amount is None: return None

        type = self.extract_transaction_type(sms_body)
        if type is None: return None

        limit = self.extract_available_limit(sms_body) if type == TransactionType.CREDIT else None
        currency = self.extract_currency(sms_body) or self.get_currency()

        return ParsedTransaction(
            amount=amount,
            type=type,
            merchant=self.extract_merchant(sms_body, sender),
            reference=self.extract_reference(sms_body),
            accountLast4=self.extract_account_last4(sms_body),
            balance=self.extract_balance(sms_body),
            creditLimit=limit,
            smsBody=sms_body,
            sender=sender,
            timestamp=timestamp,
            bankName=self.get_bank_name(),
            isFromCard=self.detect_is_card(sms_body),
            currency=currency
        )

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "SCHWAB" or "CHARLES SCHWAB" in up or "SCHWAB BANK" in up or \
               up == "24465" or re.match(r"^[A-Z]{2}-SCHWAB-[A-Z]$", up)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [
            re.compile(r"A\s+\$([0-9,]+(?:\.[0-9]{2})?)\s+debit card transaction", re.I),
            re.compile(r"A\s+\$([0-9,]+(?:\.[0-9]{2})?)\s+ATM transaction", re.I),
            re.compile(r"A\s+\$([0-9,]+(?:\.[0-9]{2})?)\s+ACH\s+transaction", re.I),
            re.compile(r"A\s+\$([0-9,]+(?:\.[0-9]{2})?)\s+ACH\s+was debited", re.I),
            re.compile(r"A\s+\$([0-9,]+(?:\.[0-9]{2})?)\s+(?:debit card|ATM)\s+transaction", re.I),
            re.compile(r"A\s+([€£₹¥฿₩ብር])\s*([0-9,]+(?:\.[0-9]{2})?)\s+debit card transaction", re.I),
            re.compile(r"A\s+([€£₹¥฿₩ብር])\s*([0-9,]+(?:\.[0-9]{2})?)\s+ATM transaction", re.I),
            re.compile(r"A\s+([€£₹¥฿₩ብር])\s*([0-9,]+(?:\.[0-9]{2})?)\s+ACH\s+transaction", re.I),
            re.compile(r"A\s+([€£₹¥฿₩ብር])\s*([0-9,]+(?:\.[0-9]{2})?)\s+ACH\s+was debited", re.I),
            re.compile(r"A\s+([€£₹¥฿₩ብር])\s*([0-9,]+(?:\.[0-9]{2})?)\s+(?:debit card|ATM)\s+transaction", re.I),
            re.compile(r"A\s+([A-Z]{3})\s*([0-9,]+(?:\.[0-9]{2})?)\s+debit card transaction", re.I),
            re.compile(r"A\s+([A-Z]{3})\s*([0-9,]+(?:\.[0-9]{2})?)\s+ATM transaction", re.I),
            re.compile(r"A\s+([A-Z]{3})\s*([0-9,]+(?:\.[0-9]{2})?)\s+ACH\s+transaction", re.I),
            re.compile(r"A\s+([A-Z]{3})\s*([0-9,]+(?:\.[0-9]{2})?)\s+ACH\s+was debited", re.I)
        ]
        for p in pats:
            m = p.search(message)
            if m:
                val = m.group(2 if m.lastindex >= 2 else 1).replace(",", "")
                try: return Decimal(val)
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(kw in low for kw in ["debit card transaction", "atm transaction", "ach transaction", "ach was debited", "was debited", "transaction was debited"]):
            return TransactionType.EXPENSE
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"account ending (\d{4})", r"account.*ending (\d{4})", r"from account ending (\d{4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_account_last4(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "reply stop to end" in low and not ("transaction" in low or "debited" in low): return False
        kw = ["debit card transaction was debited", "atm transaction was debited", "ach was debited", "transaction was debited from account"]
        return any(k in low for k in kw) or super().is_transaction_message(message)

    def detect_is_card(self, message: str) -> bool:
        low = message.lower()
        if "debit card transaction" in low or "atm transaction" in low: return True
        if "ach transaction" in low: return False
        return super().detect_is_card(message)
