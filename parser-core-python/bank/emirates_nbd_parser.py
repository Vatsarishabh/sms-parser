import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from uae_bank_parser import UAEBankParser
from transaction_type import TransactionType

class EmiratesNBDParser(UAEBankParser):
    """
    Parser for Emirates NBD Bank (UAE) transactions.
    Inherits from UAEBankParser for multi-currency support.
    """

    def get_bank_name(self) -> str:
        return "Emirates NBD"

    def can_handle(self, sender: str) -> bool:
        norm = re.sub(r"\s+", "", sender.upper())
        return any(k in norm for k in ["EMIRATESNBD", "ENBD", "EMIRATESNB"])

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        kw = ["purchase of", "debited", "credited", "withdrawn", "deposited", "transfer"]
        return any(k in low for k in kw)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"at\s+(.+?)(?:\.\s*Avl|$)", message, re.I)
        if m:
            merch = m.group(1).strip()
            if merch: return self.clean_merchant_name(merch)
            
        m = re.search(r"to\s+([A-Z][A-Z0-9\s]+?)(?:\s+on|\s+\(|$)", message, re.I)
        if m:
            merch = m.group(1).strip()
            if merch: return self.clean_merchant_name(merch)
            
        return None

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"ending\s+(\d{4})", message, re.I)
        if m: return m.group(1)
        
        m = re.search(r"[xX]{4}(\d{4})", message)
        if m: return m.group(1)
        return None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [re.compile(r"(?:Avl\s+Bal|Available\s+Balance)(?:\s+is)?\s*([A-Z]{3})\s+([\d,]+(?:\.\d{2})?)", re.I),
                re.compile(r"Available\s+Balance:\s*([A-Z]{3})\s+([\d,]+(?:\.\d{2})?)", re.I)]
        for p in pats:
            m = p.search(message)
            if m:
                try: return Decimal(m.group(2).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_available_limit(self, message: str) -> Optional[Decimal]:
        pats = [re.compile(r"Avl\s+Cr\.?\s+Limit(?:\s+is)?\s*([A-Z]{3})\s+([\d,]+(?:\.\d{2})?)", re.I),
                re.compile(r"Available\s+Credit\s+Limit:\s*([A-Z]{3})\s+([\d,]+(?:\.\d{2})?)", re.I)]
        for p in pats:
            m = p.search(message)
            if m:
                try: return Decimal(m.group(2).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_available_limit(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(kw in low for kw in ["credited", "deposited", "refund", "cashback", "received"]): return TransactionType.INCOME
        if "purchase of" in low and "credit card" in low: return TransactionType.CREDIT
        if any(kw in low for kw in ["debited", "withdrawn", "transfer"]): return TransactionType.EXPENSE
        return super().extract_transaction_type(message)
