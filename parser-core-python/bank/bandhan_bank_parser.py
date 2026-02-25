import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser

class BandhanBankParser(BaseIndianBankParser):
    """
    Parser for Bandhan Bank transaction SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Bandhan Bank"

    def can_handle(self, sender: str) -> bool:
        s = sender.upper()
        if "BANDHAN" in s: return True
        pats = [r"^[A-Z]{2}-BDNSMS(?:-S)?$", r"^[A-Z]{2}-BANDHN(?:-S)?$"]
        return any(re.match(p, s) for p in pats)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        match = re.search(r"towards\s+([^\.\n]+?)(?:\s+Value|\s+on|\s+dt|\s+at|\.|$)", message, re.IGNORE_CASE)
        if match:
            raw = match.group(1).strip()
            if "/" in raw:
                segs = [s.strip() for s in raw.split('/') if s.strip()]
                candidate = None
                for seg in reversed(segs):
                    if len(seg) >= 2 and any(c.isalpha() for c in seg) and seg.upper() != "UPI":
                        candidate = seg
                        break
                if candidate: raw = candidate
                elif segs: raw = segs[-1]
            
            cleaned = self.clean_merchant_name(re.sub(r"\bu\b", "", raw, flags=re.IGNORE_CASE).strip())
            norm = "Interest" if cleaned.lower() == "interest" else cleaned
            if self.is_valid_merchant_name(norm): return norm
        return super().extract_merchant(message, sender)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"UPI/[A-Z]{2}/([A-Z0-9]+)", message, re.IGNORE_CASE)
        if m: return m.group(1)
        return super().extract_reference(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m = re.search(r"Clear\s+Bal\s+(?:is\s+)?(?:INR\s*)?([0-9,]+(?:\.\d{2})?)", message, re.IGNORE_CASE)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)
