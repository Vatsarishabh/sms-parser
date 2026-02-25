import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Optional, List, Any
from dataclasses import dataclass

from bank_parser import BankParser
from compiled_patterns import CompiledPatterns
from mandate_info import MandateInfo

class BaseIndianBankParser(BankParser):
    """
    Base abstract class for Indian bank parsers.
    Handles common patterns across Indian banks (INR currency, UPI, etc.).
    """

    def get_currency(self) -> str:
        return "INR"

    def is_investment_transaction(self, lower_message: str) -> bool:
        """
        Checks if the message is for an investment transaction.
        Contains keywords specific to Indian investment platforms and terms.
        """
        investment_keywords = [
            "iccl", "indian clearing corporation", "nsccl", "nse clearing", "clearing corporation",
            "nach", "ach", "ecs",
            "groww", "zerodha", "upstox", "kite", "kuvera", "paytm money", "etmoney",
            "coin by zerodha", "smallcase", "angel one", "angel broking", "5paisa",
            "icici securities", "icici direct", "hdfc securities", "kotak securities",
            "motilal oswal", "sharekhan", "edelweiss", "axis direct", "sbi securities",
            "mutual fund", "sip", "elss", "ipo", "folio", "demat", "stockbroker",
            "digital gold", "sovereign gold", "nse", "bse", "cdsl", "nsdl"
        ]
        return any(keyword in lower_message for keyword in investment_keywords)

    def is_e_mandate_notification(self, message: str) -> bool:
        """Checks if this is an E-Mandate notification (not a transaction)."""
        lower_message = message.lower()
        return ("e-mandate" in lower_message or 
                "upi-mandate" in lower_message or 
                ("mandate" in lower_message and "successfully created" in lower_message))

    def is_future_debit_notification(self, message: str) -> bool:
        """Checks if this is a future debit notification."""
        lower_message = message.lower()
        return ("will be debited" in lower_message or 
                "mandate set for" in lower_message or 
                ("upcoming" in lower_message and "mandate" in lower_message))

    def parse_mandate_subscription(self, message: str) -> Optional[MandateInfo]:
        """Parses combined Mandate / E-Mandate / UPI-Mandate subscription information."""
        if not self.is_e_mandate_notification(message) and not self.is_future_debit_notification(message):
            return None

        # 1. Extract amount
        amount = None
        match = CompiledPatterns.Amount.INR_PATTERN.search(message)
        if match:
            try:
                amount = Decimal(match.group(1).replace(",", ""))
            except (InvalidOperation, ValueError):
                pass
        
        if amount is None:
            match = CompiledPatterns.Amount.RS_PATTERN.search(message)
            if match:
                try:
                    amount = Decimal(match.group(1).replace(",", ""))
                except (InvalidOperation, ValueError):
                    pass
        
        if amount is None:
            return None

        # 2. Extract merchant
        merchant = "Unknown Subscription"
        merchant_patterns = [
            re.compile(r"towards\s+([^.\n]+?)(?:\s+from|\s+A/c|\s+UMRN|\s+ID:|\s+Alert:|\s*\.|$)", re.IGNORE_CASE),
            re.compile(r"for\s+([^.\n]+?)(?:\s+ID:|\s+Act:|\s*\.|$)", re.IGNORE_CASE),
            re.compile(r"Info:\s*([^.\n]+?)(?:\s*$)", re.IGNORE_CASE)
        ]

        for pattern in merchant_patterns:
            match = pattern.search(message)
            if match:
                m = self.clean_merchant_name(match.group(1).strip())
                if self.is_valid_merchant_name(m):
                    merchant = m
                    break

        # 3. Extract date
        date_pattern = re.compile(rf"(?:on|for)\s+({CompiledPatterns.Date.DD_MMM_YY.pattern}|{CompiledPatterns.Date.DD_MM_YYYY.pattern})", re.IGNORE_CASE)
        match = date_pattern.search(message)
        date_str = match.group(1) if match else None

        # 4. Extract UMN
        umn_pattern = re.compile(r"UMN[:\s]+([^.\s]+)", re.IGNORE_CASE)
        match = umn_pattern.search(message)
        umn = match.group(1) if match else None

        class GenericMandateInfo(MandateInfo):
            def __init__(self, amt, dt, merch, u):
                self._amount = amt
                self._next_deduction_date = dt
                self._merchant = merch
                self._umn = u
            
            @property
            def amount(self): return self._amount
            @property
            def next_deduction_date(self): return self._next_deduction_date
            @property
            def merchant(self): return self._merchant
            @property
            def umn(self): return self._umn
            @property
            def date_format(self): return "dd-MMM-yy"

        return GenericMandateInfo(amount, date_str, merchant, umn)

    def is_balance_update_notification(self, message: str) -> bool:
        """Checks if this is a balance update notification (not a transaction)."""
        lower_message = message.lower()
        has_balance_keyword = any(keyword in lower_message for keyword in [
            "available bal", "avl bal", "account balance", "a/c balance", "updated balance"
        ])

        has_txn_keyword = any(keyword in lower_message for keyword in [
            "debited", "credited", "withdrawn", "spent", "transferred", "payment of"
        ])

        return has_balance_keyword and not has_txn_keyword

    @dataclass
    class BaseBalanceUpdateInfo:
        bank_name: str
        account_last4: Optional[str]
        balance: Decimal
        as_of_date: Optional[datetime] = None

    def parse_balance_update(self, message: str) -> Optional[BaseBalanceUpdateInfo]:
        if not self.is_balance_update_notification(message):
            return None

        account_last4 = self.extract_account_last4(message)
        balance = self.extract_balance(message)
        
        if balance is None:
            return None

        return self.BaseBalanceUpdateInfo(
            bank_name=self.get_bank_name(),
            account_last4=account_last4,
            balance=balance
        )

    def _get_month_number(self, month_abbr: str) -> int:
        months = {
            "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
            "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
        }
        return months.get(month_abbr.upper(), 1)
