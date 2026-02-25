import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class NMBBankParser(BankParser):
    """
    Parser for NMB Bank (Nabil Bank - Nepal) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "NMB Bank"

    def get_currency(self) -> str:
        return "NPR"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "NMB" in up or up in ["NMB_ALERT", "NMBBANK"] or "NABIL" in up

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"NPR\s+([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        m2 = re.search(r"of\s+([0-9,]+(?:\.\d{2})?)\s+is successful", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "fund transfer" in low or ("transfer" in low and "to a/c" in low): return TransactionType.EXPENSE
        if "withdrawn" in low: return TransactionType.EXPENSE
        if "wallet load" in low or "esewa wallet" in low: return TransactionType.EXPENSE
        if "deposited" in low or "credited" in low: return TransactionType.INCOME
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "fund transfer" in low or "transfer" in low: return "Fund Transfer"
        if "withdrawn" in low:
            m = re.search(r"at\s+([^.\n]+?)(?:\s+on|\.)", message, re.I)
            if m:
                loc = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(loc): return f"ATM - {loc}"
            return "ATM Withdrawal"
        if re.search(r"Esewa Wallet Load for\s+(\d+)", message, re.I): return "Esewa Wallet Load"
        if "wallet load" in low: return "Wallet Load"
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"A/C\s+(\d{8,})", message, re.I)
        if m1: return m1.group(1)[-4:]
        m2 = re.search(r"A/C\s+(\d+)#(\d+)", message, re.I)
        if m2:
            comb = m2.group(1) + m2.group(2)
            return comb[-4:] if len(comb) >= 4 else comb.zfill(4)
        m3 = re.search(r"to A/C\s+(\d+)", message, re.I)
        if m3: return m3.group(1)[-4:]
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"\(FBS:D:FPQR:(\d+)\)", message)
        if m1: return m1.group(1)
        m2 = re.search(r"Ref(?:erence)?[:\s]+([A-Z0-9]+)", message, re.I)
        if m2: return m2.group(1)
        return None

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "password"]): return False
        if "click here to learn more" in low and "withdrawn" not in low: return False
        kw = ["fund transfer", "withdrawn", "deposited", "wallet load", "successful", "credited"]
        return any(k in low for k in kw)
