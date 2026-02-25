import re
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class SliceParser(BankParser):
    """
    Parser for Slice payments bank transactions.
    """

    def get_bank_name(self) -> str:
        return "Slice"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "SLICE" in up or "SLICEIT" in up or "SLCEIT" in up

    def is_transaction_message(self, message: str) -> bool:
        if "sent" in message.lower(): return True
        return super().is_transaction_message(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        
        m1 = re.search(r"sent.*to\s+([A-Z][A-Z0-9\s./&-]+?)\s*\(", message, re.I)
        if m1:
            mer = m1.group(1).strip()
            if mer: return self.clean_merchant_name(mer)
            
        m2 = re.search(r"from\s+([A-Z][A-Z0-9\s]+?)(?:\s+on|\s+\(|$)", message, re.I)
        if m2:
            mer = m2.group(1).strip()
            if mer and mer.upper() != "NEFT": return self.clean_merchant_name(mer)
            
        if "paypal" in low: return "PayPal"
        if "slice" in low and "credited" in low: return "Slice Credit"
        
        sup = super().extract_merchant(message, sender)
        return sup if sup else "Slice"

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(k in low for k in ["credited", "received", "cashback", "refund"]):
            return TransactionType.INCOME
        if any(k in low for k in ["debited", "spent", "paid", "sent", "payment"]) and "received" not in low:
            return TransactionType.CREDIT
        return super().extract_transaction_type(message)
