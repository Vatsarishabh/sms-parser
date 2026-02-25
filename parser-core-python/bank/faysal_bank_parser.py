import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class FaysalBankParser(BankParser):
    """
    Parser for Faysal Bank (Pakistan) app notifications and SMS.
    """

    def get_bank_name(self) -> str:
        return "Faysal Bank"

    def get_currency(self) -> str:
        return "PKR"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper().replace(" ", "")
        return "FAYSAL" in norm or "FBL" in norm or "AVANZA.AMBITWIZFBL" in norm or norm == "8756"

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        has_currency = "pkr" in low
        kw = ["sent to", "transfer", "ibft", "received", "debit card purchase", "atm cash withdrawal"]
        return has_currency and any(k in low for k in kw)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"PKR\s*([0-9.,]+)", message, re.I)
        if m:
            raw = m.group(1).replace(",", "")
            if raw.count('.') > 1:
                last_dot = raw.rfind('.')
                whole = raw[:last_dot].replace(".", "")
                frac = raw[last_dot+1:]
                raw = f"{whole}.{frac}"
            try: return Decimal(raw)
            except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "debit card purchase" in low or "atm cash withdrawal" in low: return TransactionType.EXPENSE
        if "sent to" in low: return TransactionType.TRANSFER
        if "received" in low or "credited" in low: return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        m = re.search(r"debit card purchase at\s+(.+?)\s+from", message, re.I)
        if m: return self.clean_merchant_name(m.group(1).replace("*", "").replace(",", "").strip())
        
        m = re.search(r"received\s+(?:pkr\s+[0-9.,]+\s+)?(?:via\s+\w+\s+)?from\s+([A-Za-z\s.]+?)\s+(?:A/C|IBAN)", message, re.I)
        if m:
            merch = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
            
        m = re.search(r"sent to\s+([A-Za-z.\s]+?)\s+A/C", message, re.I)
        if m: return re.sub(r"\s+", " ", m.group(1).strip())
        
        if "atm cash withdrawal" in low: return "ATM Cash Withdrawal"
        if "received from" in low:
            m = re.search(r"received from\s+([A-Za-z\s.]+)", message, re.I)
            if m:
                merch = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(merch): return merch
                
        return "IBFT Transfer"

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"FBL\s+A/C\s*[*#Xx]+(\d{4})", r"A/c\s*#?\s*[*#Xx]+(\d{4})", r"A/C\s*[*#Xx]+(\d{4})"]
        for p in pats:
            m_list = list(re.finditer(p, message, re.I))
            if m_list: return m_list[-1].group(1)
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"Ref\s*#?:?\s*([A-Za-z0-9-]+)", message, re.I)
        if m: return m.group(1)
        return super().extract_reference(message)

    def detect_is_card(self, message: str) -> bool:
        if "debit card purchase" in message.lower(): return True
        return super().detect_is_card(message)
