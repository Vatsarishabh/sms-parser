import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class IPPBParser(BankParser):
    """
    Parser for India Post Payments Bank (IPPB) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "India Post Payments Bank"

    def can_handle(self, sender: str) -> bool:
        return bool(re.match(r"^[A-Z]{2}-IPBMSG-[ST]$", sender.upper()))

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Rs\.?\s*([\d,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"[Aa]/[Cc]\s+X?(\d+)", message, re.I)
        if m:
            val = m.group(1)
            return val[-4:] if len(val) >= 4 else val
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Avl\s+Bal\s+Rs\.?\s*([\d,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "debit" in low:
            m = re.search(r"to\s+([^\s]+(?:@[^\s]+)?)", message, re.I)
            if m:
                merch = m.group(1).strip()
                if "@" in merch: merch = merch.split("@")[0]
                return self.clean_merchant_name(merch)
            if "for upi" in low: return "UPI Payment"
            
        if "received a payment" in low:
            m = re.search(r"from\s+(.+?)\s+thru", message, re.I)
            if m: return self.clean_merchant_name(m.group(1).strip())
            
        return super().extract_merchant(message, sender)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"Ref\s+(\d+)", message, re.I)
        if m: return m.group(1)
        m = re.search(r"Info:\s*UPI/[^/]+/(\d+)", message, re.I)
        if m: return m.group(1)
        return super().extract_reference(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "debit" in low: return TransactionType.EXPENSE
        if "received a payment" in low: return TransactionType.INCOME
        if "credit" in low and "info: upi/credit" in low: return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["debit rs", "received a payment"]) or \
           ("info: upi" in low and "credit" in low):
            return True
        return super().is_transaction_message(message)
