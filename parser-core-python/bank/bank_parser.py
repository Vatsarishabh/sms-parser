import re
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from typing import Optional, List

from compiled_patterns import CompiledPatterns
from constants import Constants
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType


class BankParser(ABC):
    """
    Base class for bank-specific message parsers.
    Each bank should extend this class and implement its specific parsing logic.
    """

    @abstractmethod
    def get_bank_name(self) -> str:
        """Returns the name of the bank this parser handles."""
        ...

    @abstractmethod
    def can_handle(self, sender: str) -> bool:
        """Checks if this parser can handle messages from the given sender."""
        ...

    def get_currency(self) -> str:
        """Returns the currency used by this bank. Defaults to INR."""
        return "INR"

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        """Parses an SMS message and extracts transaction information."""
        if not self.is_transaction_message(sms_body):
            return None

        amount = self.extract_amount(sms_body)
        if amount is None:
            return None

        txn_type = self.extract_transaction_type(sms_body)
        if txn_type is None:
            return None

        available_limit = None
        if txn_type == TransactionType.CREDIT:
            available_limit = self.extract_available_limit(sms_body)

        return ParsedTransaction(
            amount=amount,
            type=txn_type,
            merchant=self.extract_merchant(sms_body, sender),
            reference=self.extract_reference(sms_body),
            account_last4=self.extract_account_last4(sms_body),
            balance=self.extract_balance(sms_body),
            credit_limit=available_limit,
            sms_body=sms_body,
            sender=sender,
            timestamp=timestamp,
            bank_name=self.get_bank_name(),
            is_from_card=self.detect_is_card(sms_body),
            currency=self.get_currency(),
        )

    # -------------------------------------------------------------------------
    # is_transaction_message
    # -------------------------------------------------------------------------
    def is_transaction_message(self, message: str) -> bool:
        lower = message.lower()

        if any(kw in lower for kw in ["otp", "one time password", "verification code"]):
            return False

        if any(kw in lower for kw in ["offer", "discount", "cashback offer", "win "]):
            return False

        if any(kw in lower for kw in [
            "has requested", "payment request", "collect request",
            "requesting payment", "requests rs", "ignore if already paid",
        ]):
            return False

        if "have received payment" in lower:
            return False

        if any(kw in lower for kw in [
            "is due", "min amount due", "minimum amount due",
            "in arrears", "is overdue", "ignore if paid",
        ]):
            return False

        if "pls pay" in lower and "min of" in lower:
            return False

        transaction_keywords = [
            "debited", "credited", "withdrawn", "deposited",
            "spent", "received", "transferred", "paid",
        ]
        return any(kw in lower for kw in transaction_keywords)

    # -------------------------------------------------------------------------
    # extract_currency
    # -------------------------------------------------------------------------
    def extract_currency(self, message: str) -> Optional[str]:
        pattern = re.compile(r'([A-Z]{3})\s*[0-9,]+(?:\.\d{2})?', re.IGNORECASE)
        m = pattern.search(message)
        if m:
            return m.group(1).upper()
        return None

    # -------------------------------------------------------------------------
    # extract_amount
    # -------------------------------------------------------------------------
    def extract_amount(self, message: str) -> Optional[Decimal]:
        for pattern in CompiledPatterns.Amount.ALL_PATTERNS:
            m = pattern.search(message)
            if m:
                try:
                    return Decimal(m.group(1).replace(",", ""))
                except InvalidOperation:
                    pass
        return None

    # -------------------------------------------------------------------------
    # extract_transaction_type
    # -------------------------------------------------------------------------
    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        lower = message.lower()

        if self.is_investment_transaction(lower):
            return TransactionType.INVESTMENT

        if lower.count("debited") > 0:
            return TransactionType.EXPENSE
        if "withdrawn" in lower:
            return TransactionType.EXPENSE
        if "spent" in lower:
            return TransactionType.EXPENSE
        if "charged" in lower:
            return TransactionType.EXPENSE
        if "paid" in lower:
            return TransactionType.EXPENSE
        if "purchase" in lower:
            return TransactionType.EXPENSE
        if "deducted" in lower:
            return TransactionType.EXPENSE

        if "credited" in lower:
            return TransactionType.INCOME
        if "deposited" in lower:
            return TransactionType.INCOME
        if "received" in lower:
            return TransactionType.INCOME
        if "refund" in lower:
            return TransactionType.INCOME
        if "cashback" in lower and "earn cashback" not in lower:
            return TransactionType.INCOME

        return None

    # -------------------------------------------------------------------------
    # is_investment_transaction
    #'Rs.5000.00 paid thru A/C XX8263 on 20-11-24 14:03:52 to ACHHRAN KUMARI UPI Ref 432526453805. If not done SMS BLOCKUPI to 9901771222.-Canara Bank '
    # -------------------------------------------------------------------------
    def is_investment_transaction(self, lower_message: str) -> bool:
        investment_keywords = [
            "iccl", "indian clearing corporation", "nsccl", "nse clearing",
            "clearing corporation", "nach", "ach", "ecs",
            "groww", "zerodha", "upstox", "kite", "kuvera",
            "paytm money", "etmoney", "coin by zerodha", "smallcase",
            "angel one", "angel broking", "5paisa",
            "icici securities", "icici direct", "hdfc securities",
            "kotak securities", "motilal oswal", "sharekhan",
            "edelweiss", "axis direct", "sbi securities",
            "mutual fund", "sip", "elss", "ipo", "folio",
            "demat", "stockbroker", "digital gold", "sovereign gold",
            "nse", "bse", "cdsl", "nsdl",
        ]
        return any(kw in lower_message for kw in investment_keywords)

    # -------------------------------------------------------------------------
    # extract_merchant
    # -------------------------------------------------------------------------
    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        for pattern in CompiledPatterns.Merchant.ALL_PATTERNS:
            m = pattern.search(message)
            if m:
                merchant = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(merchant):
                    return merchant
        return None

    # -------------------------------------------------------------------------
    # extract_reference
    # -------------------------------------------------------------------------
    def extract_reference(self, message: str) -> Optional[str]:
        for pattern in CompiledPatterns.Reference.ALL_PATTERNS:
            m = pattern.search(message)
            if m:
                return m.group(1).strip()
        return None

    # -------------------------------------------------------------------------
    # extract_account_last4
    # -------------------------------------------------------------------------
    def extract_account_last4(self, message: str) -> Optional[str]:
        for pattern in CompiledPatterns.Account.ALL_PATTERNS:
            m = pattern.search(message)
            if m:
                last4 = m.group(1)
                if self._is_valid_account_last4(last4, m.group(0), message):
                    return last4
        return None

    def _is_valid_account_last4(self, last4: str, matched_text: str, full_message: str) -> bool:
        escaped = re.escape(last4)

        date_patterns = [
            re.compile(r'\d{1,2}[/-]\d{1,2}[/-]' + escaped),
            re.compile(escaped + r'[/-]\d{1,2}[/-]\d{1,2}'),
            re.compile(r'\bon\s+\d{1,2}[/-]\d{1,2}[/-]' + escaped, re.IGNORECASE),
            re.compile(r'\bdated\s+\d{1,2}[/-]\d{1,2}[/-]' + escaped, re.IGNORECASE),
        ]
        for dp in date_patterns:
            if dp.search(full_message):
                return False

        rrn_patterns = [
            re.compile(r'RRN\s+(?:No\.?)?(\d{8,16})', re.IGNORECASE),
            re.compile(r'Ref\s+(?:No\.?)?(\d{8,16})', re.IGNORECASE),
        ]
        for rp in rrn_patterns:
            rm = rp.search(full_message)
            if rm and last4 in rm.group(1):
                return False

        try:
            val = int(last4)
            if 2000 <= val <= 2099:
                year_ctx = [
                    re.compile(r'\bon\s+\d{1,2}[/-]\d{1,2}[/-]' + escaped, re.IGNORECASE),
                    re.compile(r'\bdated\s+.*?' + escaped, re.IGNORECASE),
                    re.compile(escaped + r'(?:\s|$)'),
                ]
                for yp in year_ctx:
                    if yp.search(full_message):
                        acct = re.compile(r'(?:A/c|Account|Acct).{0,25}' + escaped, re.IGNORECASE)
                        if not acct.search(full_message):
                            return False
        except ValueError:
            pass

        return True

    # -------------------------------------------------------------------------
    # extract_balance
    # -------------------------------------------------------------------------
    def extract_balance(self, message: str) -> Optional[Decimal]:
        for pattern in CompiledPatterns.Balance.ALL_PATTERNS:
            m = pattern.search(message)
            if m:
                try:
                    return Decimal(m.group(1).replace(",", ""))
                except InvalidOperation:
                    pass
        return None

    # -------------------------------------------------------------------------
    # extract_available_limit
    # -------------------------------------------------------------------------
    def extract_available_limit(self, message: str) -> Optional[Decimal]:
        credit_limit_patterns = [
            re.compile(r'Available\s+limit\s+Rs\.([0-9,]+(?:\.\d{2})?)', re.IGNORECASE),
            re.compile(r'Available\s+limit:?\s*Rs\.?\s*([0-9,]+(?:\.\d{2})?)', re.IGNORECASE),
            re.compile(r'Avl\s+Lmt:?\s*Rs\.?\s*([0-9,]+(?:\.\d{2})?)', re.IGNORECASE),
            re.compile(r'Avail\s+Limit:?\s*Rs\.?\s*([0-9,]+(?:\.\d{2})?)', re.IGNORECASE),
            re.compile(r'Available\s+Credit\s+Limit:?\s*Rs\.?\s*([0-9,]+(?:\.\d{2})?)', re.IGNORECASE),
            re.compile(r'(?:^|\s)Limit:?\s*Rs\.?\s*([0-9,]+(?:\.\d{2})?)', re.IGNORECASE),
        ]
        for pattern in credit_limit_patterns:
            m = pattern.search(message)
            if m:
                try:
                    return Decimal(m.group(1).replace(",", ""))
                except InvalidOperation:
                    pass
        return None

    # -------------------------------------------------------------------------
    # detect_is_card
    # -------------------------------------------------------------------------
    def detect_is_card(self, message: str) -> bool:
        lower = message.lower()

        account_patterns = [
            "a/c", "account", "ac ", "acc ",
            "saving account", "current account",
            "savings a/c", "current a/c",
        ]
        if any(p in lower for p in account_patterns):
            return False

        card_patterns = [
            "card ending", "card xx", "debit card", "credit card",
            "card no.", "card number", "card *", "card x",
        ]
        if any(p in lower for p in card_patterns):
            return True

        masked_card_regex = re.compile(r'(?:xx|XX|\*{2,})?\d{4}')
        if "ending" in lower and masked_card_regex.search(message):
            return True

        return False

    # -------------------------------------------------------------------------
    # clean_merchant_name
    # -------------------------------------------------------------------------
    def clean_merchant_name(self, merchant: str) -> str:
        result = merchant
        result = CompiledPatterns.Cleaning.TRAILING_PARENTHESES.sub("", result)
        result = CompiledPatterns.Cleaning.REF_NUMBER_SUFFIX.sub("", result)
        result = CompiledPatterns.Cleaning.DATE_SUFFIX.sub("", result)
        result = CompiledPatterns.Cleaning.UPI_SUFFIX.sub("", result)
        result = CompiledPatterns.Cleaning.TIME_SUFFIX.sub("", result)
        result = CompiledPatterns.Cleaning.TRAILING_DASH.sub("", result)
        result = CompiledPatterns.Cleaning.PVT_LTD.sub("", result)
        result = CompiledPatterns.Cleaning.LTD.sub("", result)
        return result.strip()

    # -------------------------------------------------------------------------
    # is_valid_merchant_name
    # -------------------------------------------------------------------------
    def is_valid_merchant_name(self, name: str) -> bool:
        common_words = {
            "USING", "VIA", "THROUGH", "BY", "WITH",
            "FOR", "TO", "FROM", "AT", "THE",
        }
        return (
            len(name) >= Constants.Parsing.MIN_MERCHANT_NAME_LENGTH
            and any(c.isalpha() for c in name)
            and name.upper() not in common_words
            and not all(c.isdigit() for c in name)
            and "@" not in name
        )
