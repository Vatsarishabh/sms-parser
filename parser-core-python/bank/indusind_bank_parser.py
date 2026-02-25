import re
from decimal import Decimal, InvalidOperation
from typing import Optional
from datetime import datetime

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class IndusIndBankParser(BaseIndianBankParser):
    """
    Parser for IndusInd Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "IndusInd Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        if norm in ["INDUSB", "INDUSIND"] or "INDUSIND BANK" in norm: return True
        pats = [r"^[A-Z]{2}-INDUSB(?:-[A-Z])?$", r"^[A-Z]{2}-INDUSIND(?:-[A-Z])?$", r"^[A-Z]{2}-INDUS(?:[A-Z]{2,})?-[A-Z]$"]
        return any(re.match(p, norm) for p in pats)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "spent" in low or "debited" in low or "purchase" in low: return TransactionType.EXPENSE
        if "deposit" in low or "fd" in low or "ach" in low: return TransactionType.INVESTMENT
        return super().extract_transaction_type(message)

    def detect_is_card(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["ach db", "ach cr", "nach"]): return False
        return super().detect_is_card(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "net interest" in low and "deposit no" in low: return False
        return super().is_transaction_message(message)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"(?:INR|Rs\.?|₹)\s*([0-9,]+(?:\.\d{2})?)\s+(?:debited|credited|spent|withdrawn|paid|purchase)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"towards\s+(\S+)", message, re.I)
        if m1:
            mer = m1.group(1).strip().stripEnd(".,;")
            if "/" in mer: mer = mer.split("/")[0]
            if "@" in mer: mer = mer.split("@")[0].strip()
            if mer: return self.clean_merchant_name(mer)
            
        m2 = re.search(r"from\s+account\s+[^\s/]+/([^\s(]+)", message, re.I)
        if m2:
            mer = m2.group(1).strip().stripEnd(".,;)")
            if mer: return self.clean_merchant_name(mer)
            
        m3 = re.search(r"from\s+(\S+)", message, re.I)
        if m3:
            tok = m3.group(1).strip().stripEnd(".,;")
            mer = tok
            if "/" in mer: mer = mer.split("/")[0]
            if "@" in mer:
                mer = mer.split("@")[0].strip()
                if mer: return self.clean_merchant_name(mer)
                
        m4 = re.search(r"at\s+([^\n]+?)(?:\s+Ref|\s+on|$)", message, re.I)
        if m4:
            mer = m4.group(1).strip()
            if mer: return self.clean_merchant_name(mer)
            
        m5 = re.search(r"/(?!\s)([^/\.\s]+)\.\s*Bal", message, re.I)
        if m5:
            mer = m5.group(1).strip()
            if mer: return self.clean_merchant_name(mer)
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"IndusInd\s+Account\s+\d+X+(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"account\s+X{5,}(\d{4})", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"A/?C\s+([0-9]{2,})[\*xX#]+(\d{4,})", message, re.I)
        if m3:
            tra = m3.group(2)
            return tra[-4:] if len(tra) >= 4 else tra
        m4 = re.search(r"A/?c\s+\*?X+\s*(\d{4,6})", message, re.I)
        if m4:
            dig = m4.group(1)
            return dig[-4:] if len(dig) >= 4 else dig
        low = message.lower()
        if any(k in low for k in ["ach db", "ach cr", "nach"]): return None
        return None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Avl\s*BAL\s+of\s+INR\s*([0-9,]+(?:\.\d{2})?)",
                r"(?:Avl\s*BAL|Available\s+Balance(?:\s+is)?|Bal)[:\s]+INR\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"RRN[:\s]+([0-9]+)", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"(?:IMPS\s+)?Ref\s+no\.?\s*([0-9]+)", message, re.I)
        if m2: return m2.group(1)
        return super().extract_reference(message)
