import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class JioPayParser(BankParser):
    """
    Parser for JioPay wallet transactions.
    """

    def get_bank_name(self) -> str:
        return "JioPay"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "JIOPAY" in up or up.endswith("-JIOPAY-S") or up.endswith("-JIOPAY-T") or up == "JM-JIOPAY"

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"Plan\s+Name\s*:\s*([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        m2 = re.search(r"Rs\.?\s*([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "recharge successful" in low and "jio number" in low:
            m = re.search(r"Jio\s+Number\s*:\s*(\d{10})", message, re.I)
            num = m.group(1) if m else ""
            return f"Jio Recharge - {num[:4]}****" if num else "Jio Recharge"
            
        if "bill payment" in low:
            if "electricity" in low: return "Electricity Bill"
            if "water" in low: return "Water Bill"
            if "gas" in low: return "Gas Bill"
            if "broadband" in low: return "Broadband Bill"
            if "dth" in low: return "DTH Recharge"
            return "Bill Payment"
            
        if "recharge" in low:
            if "mobile" in low: return "Mobile Recharge"
            if "dth" in low: return "DTH Recharge"
            if "data" in low: return "Data Recharge"
            return "Recharge"
            
        if "payment successful to" in low:
            m = re.search(r"payment\s+successful\s+to\s+([^.\n]+)", message, re.I)
            if m: return self.clean_merchant_name(m.group(1).strip())
            return "JioPay Payment"
            
        return super().extract_merchant(message, sender) or "JioPay Transaction"

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"Transaction\s+ID\s*:\s*([A-Z0-9]+)", message, re.I)
        return m.group(1) if m else super().extract_reference(message)

    def extract_transaction_type(self, message: str) -> TransactionType:
        return TransactionType.CREDIT

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["e-bill", "bill has been sent", "bill summary", "payment due date", "amount payable"]): return False
        return "recharge successful" in low or super().is_transaction_message(message)
