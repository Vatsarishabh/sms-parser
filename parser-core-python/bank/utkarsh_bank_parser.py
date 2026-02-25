import re
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class UtkarshBankParser(BaseIndianBankParser):
    """
    Parser for Utkarsh Small Finance Bank (SFBL) SuperCard credit card transactions.
    """

    def get_bank_name(self) -> str:
        return "Utkarsh Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return "UTKSPR" in up or "UTKARSH" in up or "UTKSFB" in up

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        m1 = re.search(r"for\s+UPI\s*[-–]\s*([^\s.]+)", message, re.I)
        if m1:
            mer = m1.group(1).strip()
            if not re.match(r"[x0-9]+", mer): return self.clean_merchant_name(mer)
            
        m2 = re.search(r"for\s+([^0-9][^\s]+?)(?:\s+on\s+|\s+at\s+|$)", message, re.I)
        if m2:
            mer = m2.group(1).strip()
            if mer.upper() not in ["UPI", "INR"]: return self.clean_merchant_name(mer)
            
        if "supercard" in low and "upi" in low: return "UPI Payment"
        sup = super().extract_merchant(message, sender)
        return sup if sup else "Utkarsh SuperCard"

    def extract_transaction_type(self, message: str) -> TransactionType:
        return TransactionType.CREDIT

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"SuperCard\s+[xX*]*(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"(?:account|a/c)\s+[xX*]*(\d{4})", message, re.I)
        if m2: return m2.group(1)
        return super().extract_account_last4(message)
