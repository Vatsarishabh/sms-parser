import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class MPESAParser(BankParser):
    """
    Parser for M-PESA (Kenya) mobile money SMS messages.
    """

    def get_bank_name(self) -> str:
        return "M-PESA"

    def get_currency(self) -> str:
        return "KES"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "MPESA" in up or "M-PESA" in up

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"Ksh([0-9,]+(?:\.[0-9]{2})?)\s+(?:paid|sent|received)", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        m2 = re.search(r"received\s+Ksh([0-9,]+(?:\.[0-9]{2})?)", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "you have received" in low or "received ksh" in low: return TransactionType.INCOME
        if "paid to" in low or "sent to" in low: return TransactionType.EXPENSE
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"paid to\s+(.+?)\s+\d+\.\s+on", message, re.I)
        if m1:
            mer = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m2 = re.search(r"sent to\s+(.+?)\s+0\d{3}\s+\d{3}\s+\d{3}", message, re.I)
        if m2:
            mer = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m3 = re.search(r"sent to\s+(.+?)\s+for account", message, re.I)
        if m3:
            mer = self.clean_merchant_name(m3.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m4 = re.search(r"received\s+(?:Ksh[0-9,]+(?:\.[0-9]{2})?\s+)?from\s+(.+?)\s+on", message, re.I)
        if m4:
            mer = m4.group(1).strip()
            if mer.endswith("."): mer = mer[:-1].strip()
            mer = re.sub(r"\s+0\d{10}$", "", mer)
            mer = re.sub(r"\s+\d{6,}$", "", mer).strip()
            mer = self.clean_merchant_name(mer)
            if self.is_valid_merchant_name(mer): return mer
            
        m5 = re.search(r"from\s+([^.]+)\.\s+on", message, re.I)
        if m5:
            mer = m5.group(1).strip()
            mer = re.sub(r"\s+0\d{10}$", "", mer)
            mer = self.clean_merchant_name(mer)
            if self.is_valid_merchant_name(mer): return mer
            
        return None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"New M-PESA balance is Ksh([0-9,]+(?:\.[0-9]{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"^([A-Z0-9]{10})\s+Confirmed", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"^([A-Z0-9]{10})\s+Confirmed\.", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"Congratulations!\s+([A-Z0-9]{10})\s+confirmed", message, re.I)
        if m3: return m3.group(1)
        return None

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "confirmed" not in low: return False
        kw = ["paid to", "sent to", "received", "new m-pesa balance"]
        return any(k in low for k in kw)

    def clean_merchant_name(self, merchant: str) -> str:
        # Avoid removing LIMITED for M-PESA as requested in original code
        m = re.sub(r"\s*\(.*?\)\s*$", "", merchant)
        m = re.sub(r"\s+Ref\s+No.*", "", m, flags=re.I)
        m = re.sub(r"\s+on\s+\d{2}.*", "", m)
        m = re.sub(r"\s+UPI.*", "", m, flags=re.I)
        m = re.sub(r"\s+at\s+\d{2}:\d{2}.*", "", m)
        m = re.sub(r"\s*-\s*$", "", m)
        return m.strip()
