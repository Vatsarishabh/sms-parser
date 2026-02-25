import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class DashenBankParser(BankParser):
    """
    Parser for Dashen Bank - handles ETB currency transactions.
    """

    def get_bank_name(self) -> str:
        return "Dashen Bank"

    def get_currency(self) -> str:
        return "ETB"

    def can_handle(self, sender: str) -> bool:
        return sender.upper().strip() == "DASHENBANK"

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"ETB\s+([0-9,]+(?:\.[0-9]{1,2})?)", message, re.I)
        if m: return self._parse_scaled_amount(m.group(1))
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(kw in low for kw in ["has been credited", "credited with", "you have received"]): return TransactionType.INCOME
        if any(kw in low for kw in ["has been debited", "debited with", "debited from"]): return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"credited to the (Telebirr account [+\d]+)", message, re.I)
        if m: return m.group(1).strip()
        
        m = re.search(r"from\s+([A-Z][A-Z\s]*?)\s+on\s+on", message, re.I)
        if m:
            merch = m.group(1).strip()
            if self.is_valid_merchant_name(merch): return merch
            
        m = re.search(r"from\s+(telebirr account number \d+\s)Ref", message, re.I)
        if m: return m.group(1).strip()

        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"(\d{4})\*+\d+", message, re.I)
        return m.group(1) if m else super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Your\s+current\s+balance\s+is\s+ETB\s+([0-9,]+(?:\.[0-9]{1,2})?)", message, re.I)
        if m: return self._parse_scaled_amount(m.group(1))
        
        m = re.search(r"Your\s+account\s+balance\s+is\s+ETB\s+([0-9,]+(?:\.[0-9]{1,2})?)", message, re.I)
        if m: return self._parse_scaled_amount(m.group(1))
        
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"(https://receipt\.dashensuperapp\.com/receipt/[^\s]+)", message, re.I)
        if m: return m.group(1)
        
        m = re.search(r"Ref\s+No:(\d+)", message, re.I)
        if m: return m.group(1)
        
        return super().extract_reference(message)

    def _parse_scaled_amount(self, raw: str) -> Optional[Decimal]:
        try:
            return Decimal(raw.replace(",", "")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            return None
