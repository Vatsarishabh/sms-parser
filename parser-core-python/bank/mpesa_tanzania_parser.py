import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class MPesaTanzaniaParser(BankParser):
    """
    Parser for M-Pesa Tanzania (Vodacom) mobile money SMS messages.
    """

    def get_bank_name(self) -> str:
        return "M-Pesa Tanzania"

    def get_currency(self) -> str:
        return "TZS"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "MPESA" in up or "M-PESA" in up or "VODACOM" in up

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        if "TZS" not in sms_body.upper(): return None
        return super().parse(sms_body, sender, timestamp)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"TZS\s+([0-9,]+(?:\.[0-9]{2})?)", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        m2 = re.search(r"TZS([0-9,]+(?:\.[0-9]{2})?)", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(k in low for k in ["you have received", "received tsh", "received tzs"]): return TransactionType.INCOME
        if any(k in low for k in ["sent to", "paid to", "withdrawn"]): return TransactionType.EXPENSE
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"from\s+([A-Z][A-Za-z\s]+?)(?:\s*\(|$)", message, re.I)
        if m1:
            mer = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m2 = re.search(r"sent to\s+([A-Z][A-Za-z\s]+?)(?:\s*\(|$)", message, re.I)
        if m2:
            mer = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m3 = re.search(r"paid to\s+([A-Za-z0-9\s]+?)(?:\s*\(Merchant|\s+on|\s*$)", message, re.I)
        if m3:
            mer = self.clean_merchant_name(m3.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m4 = re.search(r"paid to\s+(\w+)\s+for\s+account", message, re.I)
        if m4: return m4.group(1).strip()
        
        return None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"New M-Pesa balance is TZS\s*([0-9,]+(?:\.[0-9]{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"^([A-Z0-9]{10})\s+Confirmed", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"^([A-Z0-9]{10})\s+Confirmed\.", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"TIPS\s+Reference[:\s]+([A-Z0-9]+)", message, re.I)
        if m3: return m3.group(1)
        return None

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "confirmed" not in low or "tzs" not in low: return False
        kw = ["received", "sent to", "paid to", "withdrawn", "new m-pesa balance"]
        return any(k in low for k in kw)

    def clean_merchant_name(self, merchant: str) -> str:
        m = re.sub(r"\s*\(.*?\)\s*$", "", merchant)
        m = re.sub(r"\s+on\s+\d{4}.*", "", m)
        m = re.sub(r"\s+at\s+\d{2}:\d{2}.*", "", m)
        m = re.sub(r"\s*-\s*$", "", m)
        return m.strip()
