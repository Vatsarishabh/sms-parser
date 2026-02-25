import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class IDBIBankParser(BankParser):
    """
    Parser for IDBI Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "IDBI Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        if any(k in norm for k in ["IDBIBK", "IDBIBANK", "IDBI"]): return True
        pats = [r"^[A-Z]{2}-IDBIBK-S$", r"^[A-Z]{2}-IDBI-S$", r"^[A-Z]{2}-IDBIBK$", r"^[A-Z]{2}-IDBI$"]
        if any(re.match(p, norm) for p in pats): return True
        return norm in ["IDBIBK", "IDBIBANK"]

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"debited\s+with\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"debited\s+for\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"credited\s+with\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        m1 = re.search(r"towards\s+([^.\n]+?)\s+for", message, re.I)
        if m1:
            merch = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
            
        m2 = re.search(r";\s*([^.\n]+?)\s+credited\.", message, re.I)
        if m2:
            merch = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
            
        if "autopay" in low or "mandate" in low:
            m3 = re.search(r"towards\s+([^.\n]+?)\s+for\s+\w*MANDATE", message, re.I)
            if m3: return self.clean_merchant_name(m3.group(1).strip())
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"Acct\s+(?:XX|X\*+)?(\d{3,4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"IDBI\s+Bank\s+Acct\s+(?:XX|X\*+)?(\d{3,4})", message, re.I)
        if m2: return m2.group(1)
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"RRN\s+([A-Za-z0-9]+)", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"UPI:([A-Za-z0-9]+)", message, re.I)
        if m2: return m2.group(1)
        return super().extract_reference(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Bal\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        # skip check logic is same as base if not overriding further
        return super().is_transaction_message(message)
