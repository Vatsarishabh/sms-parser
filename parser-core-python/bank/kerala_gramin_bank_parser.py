import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class KeralaGraminBankParser(BaseIndianBankParser):
    """
    Parser for Kerala Gramin Bank (India) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Kerala Gramin Bank"

    def get_currency(self) -> str:
        return "INR"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "KGBANK" in up or "KERALA GRAMIN" in up or "KERALAGR" in up

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"(?:debited for|credited with)\s+(?:Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "debited for" in low or "is debited" in low: return TransactionType.EXPENSE
        if "credited with" in low or "is credited" in low: return TransactionType.INCOME
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "debited" in low and "credited to" in low: return "UPI Transfer"
        
        m = re.search(r"from\s+([^.\s]+@[a-z]+)", message, re.I)
        if m:
            upi_id = m.group(1).strip()
            name_part = upi_id.split("@")[0]
            if re.match(r"^\d+$", name_part): return "UPI Payment"
            return self.clean_merchant_name(name_part) if name_part else "UPI Payment"
            
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"(?:a/c no\.|Account)\s+(?:XXXX|XX)(\d{3,5})", message, re.I)
        if m:
            dig = m.group(1)
            return dig[-4:] if len(dig) >= 4 else dig.zfill(4)
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"UPI Ref\.?\s*no\.?\s*(\d+)", message, re.I)
        return m.group(1) if m else None

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "password"]): return False
        kw = ["debited for", "is debited", "credited with", "is credited"]
        return any(k in low for k in kw)
