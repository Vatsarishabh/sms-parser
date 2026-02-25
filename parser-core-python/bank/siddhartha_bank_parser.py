import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class SiddharthaBankParser(BankParser):
    """
    Parser for Siddhartha Bank Limited (Nepal) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Siddhartha Bank"

    def get_currency(self) -> str:
        return "NPR"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper().replace("-", "_")
        return "SBL" in up or up == "SBL_ALERT" or "SIDDHARTHA" in up

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"NPR\s+([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "withdrawn" in low: return TransactionType.EXPENSE
        if "deposited" in low or "credited" in low: return TransactionType.INCOME
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        
        m1 = re.search(r"qr payment to\s+([^-\n]+?)(?:\s+-|$)", message, re.I)
        if m1:
            mer = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        if "nea" in low: return "Nepal Electricity Authority"
        
        if "fund trf to" in low or "fund transfer to" in low:
            return "Fund Transfer (IBFT)" if "ibft" in low else "Fund Transfer"
            
        if "fund trf frm" in low or "fund transfer from" in low:
            return "Fund Transfer (IBFT)" if "ibft" in low else "Fund Transfer"
            
        if "deposited" in low: return "Deposit"
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"AC\s+###[X#]+(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"AC\s+[X#]+(\d{4})", message, re.I)
        if m2: return m2.group(1)
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"\(IN-(\d+)", message)
        if m1: return f"IN-{m1.group(1)}"
        m2 = re.search(r"IBFT:(\d+)", message)
        if m2: return m2.group(1)
        m3 = re.search(r"FON:IBFT:(\d+)", message)
        if m3: return m3.group(1)
        return None

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "password", "verification code"]): return False
        has_amt = "npr" in low
        kw = ["withdrawn", "deposited", "fund trf", "fund transfer", "qr payment"]
        return has_amt and any(k in low for k in kw)
