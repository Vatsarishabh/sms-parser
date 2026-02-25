import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class EverestBankParser(BankParser):
    """
    Parser for Everest Bank (Nepal) - handles NPR currency transactions.
    """

    def get_bank_name(self) -> str:
        return "Everest Bank"

    def get_currency(self) -> str:
        return "NPR"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if re.match(r"^\d{7,10}$", sender): return True
        return up == "EVEREST" or "EVERESTBANK" in up or up == "UJJ SH" or up == "CWRD" or \
               re.match(r"^[A-Z]{2}-EVEREST-[A-Z]$", up)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"NPR\s+([0-9,]+(?:\.[0-9]{2})?)\s",
                r"NPR\s+([0-9,]+(?:\.[0-9]{2})?)(?:\s|$)",
                r"(?:debited|credited)\s+by\s+NPR\s+([0-9,]+(?:\.[0-9]{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "is debited" in low or "debited by" in low: return TransactionType.EXPENSE
        if "is credited" in low or "credited by" in low: return TransactionType.INCOME
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r"For:\s*([^.]+?)(?:\.\s|$)", message, re.I)
        if m:
            content = m.group(1).strip()
            if content.lower().startswith("cwdr/"): return "ATM Withdrawal"
            if "/" in content and "," in content:
                parts = content.split(",")
                if len(parts) >= 2:
                    before = parts[0].strip()
                    after = parts[1].strip()
                    if "/" in before:
                        s_parts = before.split("/")
                        if len(s_parts) >= 2:
                            pt = s_parts[1].strip()
                            if pt and not re.match(r"\d+", pt): return self.clean_merchant_name(pt)
                    if after and after != "UJJ SH": return self.clean_merchant_name(after)
                
                parts_all = content.replace(",", "/").split("/")
                for p in parts_all:
                    p_cl = p.strip()
                    if p_cl and not re.match(r"\d+", p_cl) and p_cl != "UJJ SH":
                        return self.clean_merchant_name(p_cl)
                return None
            if content: return self.clean_merchant_name(content)
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"A/c\s+([^\s]+)", message, re.I)
        if m:
            acc = m.group(1).strip()
            if acc != "{Account}" and len(acc) >= 4: return acc[-4:]
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"For:\s*([^.]+?)(?:\.\s|$)", message, re.I)
        if m:
            content = m.group(1).strip()
            if "CWDR/" in content:
                parts = content.split("/")
                if len(parts) >= 3: return f"{parts[1]}/{parts[2]}"
            rm = re.search(r"(\d{6,})", content)
            if rm: return rm.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        kw = ["dear customer", "your a/c", "is debited", "is credited", "debited by", "credited by", "for:", "never share password", "npr"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
