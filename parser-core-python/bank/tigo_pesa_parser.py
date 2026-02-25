import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class TigoPesaParser(BankParser):
    """
    Parser for Tigo Pesa / Mixx by Yas (Tanzania) mobile money SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Tigo Pesa"

    def get_currency(self) -> str:
        return "TZS"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return any(k in up for k in ["TIGOPESA", "TIGO PESA", "MIXX BY YAS", "MIXXBYYAS"]) or up == "TIGO"

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"Cash-In of TSh\s*([0-9,]+(?:\.[0-9]{2})?)",
                r"sent TSh\s*([0-9,]+(?:\.[0-9]{2})?)",
                r"received TSh\s*([0-9,]+(?:\.[0-9]{2})?)",
                r"paid TSh\s*([0-9,]+(?:\.[0-9]{2})?)",
                r"You have sent TSh\s*([0-9,]+(?:\.[0-9]{2})?)",
                r"You have paid TSh\s*([0-9,]+(?:\.[0-9]{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        
        m_fallback = re.search(r"TSh\s*([0-9,]+(?:\.[0-9]{2})?)", message, re.I)
        if m_fallback:
            try: return Decimal(m_fallback.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "cash-in" in low: return TransactionType.INCOME
        if any(k in low for k in ["you have received", "received tsh"]) or ("transfer successful" in low and "received" in low):
            return TransactionType.INCOME
        if "you have sent" in low or "you have paid" in low: return TransactionType.EXPENSE
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"from Agent\s*-?\s*([A-Z][A-Za-z\s]+?)\s+is\s+successful", message, re.I)
        if m1:
            mer = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(mer): return f"Agent - {mer}"
            
        m2 = re.search(r"to\s+[\dX]+\s*-\s*([A-Z][A-Za-z\s]+?)(?:\.|Total|$)", message, re.I)
        if m2:
            mer = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m3 = re.search(r"paid\s+TSh\s*[0-9,]+(?:\.[0-9]{2})?\s+to\s+([A-Za-z0-9\s&]+?)(?:\.|Charges|$)", message, re.I)
        if m3:
            mer = self.clean_merchant_name(m3.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m4 = re.search(r"from\s+(TIPS\.[A-Za-z0-9_.]+)", message, re.I)
        if m4:
            src = m4.group(1)
            if "Selcom" in src: return "Selcom (TIPS Transfer)"
            if "NMB" in src: return "NMB Bank (TIPS Transfer)"
            if "CRDB" in src: return "CRDB Bank (TIPS Transfer)"
            return "TIPS Transfer"
            
        m5 = re.search(r"to\s+([A-Z][A-Za-z\s]+?)(?:\.|,|Charges|Total|$)", message, re.I)
        if m5:
            mer = self.clean_merchant_name(m5.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
        return None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"New balance is TSh\s*([0-9,]+(?:\.[0-9]{2})?)",
                r"Your New balance is TSh\s*([0-9,]+(?:\.[0-9]{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"TxnId:\s*(\d+)", r"TxnID:\s*(\d+)", r"Trnx ID:\s*(\d+)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        m_tips = re.search(r"with TxnId:\s*\d+\.\s*([A-Z0-9_]+)", message, re.I)
        if m_tips: return m_tips.group(1)
        return None

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "tsh" not in low: return False
        kw = ["cash-in", "you have sent", "you have paid", "you have received", "transfer successful", "is successful", "new balance"]
        return any(k in low for k in kw)

    def clean_merchant_name(self, merchant: str) -> str:
        m = re.sub(r"\s*\(.*?\)\s*$", "", merchant)
        m = re.sub(r"\s+on\s+\d{2}/.*", "", m)
        m = re.sub(r"\s*-\s*$", "", m)
        m = re.sub(r"^\s*-\s*", "", m)
        return m.strip()
