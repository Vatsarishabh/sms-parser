import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class AxisBankParser(BaseIndianBankParser):
    """
    Parser for Axis Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Axis Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        if any(kw in norm for kw in ["AXIS BANK", "AXISBANK", "AXISBK", "AXISB"]):
            return True
        pats = [r"^[A-Z]{2}-AXISBK-S$", r"^[A-Z]{2}-AXISBANK-S$", r"^[A-Z]{2}-AXIS-S$", r"^[A-Z]{2}-AXISBK$", r"^[A-Z]{2}-AXIS$"]
        if any(re.match(p, norm) for p in pats): return True
        return norm in ["AXISBK", "AXISBANK", "AXIS"]

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [
            re.compile(r"INR\s+([0-9,]+(?:\.\d{2})?)\s+debited", re.IGNORECASE),
            re.compile(r"INR\s+([0-9,]+(?:\.\d{2})?)\s+credited", re.IGNORECASE),
            re.compile(r"Payment\s+of\s+INR\s+([0-9,]+(?:\.\d{2})?)", re.IGNORECASE)
        ]
        for p in pats:
            m = p.search(message)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        lower = message.lower()
        if "debited from a/c no." in lower and " on axis bank" in lower: return "ATM"
        if ("atm" in lower or "cash withdrawal" in lower) and "debited" in lower: return "ATM"

        match = re.search(r"debited from A/c no\. [^\s]+ on ([^0-9]+?)(?:\d{2}-\d{2}-\d{4})", message, re.IGNORECASE)
        if match:
            merch = self.clean_merchant_name(match.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch

        spent_ist = re.compile(r"Spent[\s\S]*?IST\s*\n\s*([^\n]+?)(?:\s*\n|\s*Avl Limit:|\s*Avl Lmt|\s*Not you?)", re.IGNORECASE)
        match = spent_ist.search(message)
        if match:
            merch = match.group(1).strip()
            merch = re.sub(r"\s+Limi$", "", merch)
            merch = re.sub(r"\s+Pay$", "", merch)
            merch = re.sub(r"\s+SUPE$", "", merch)
            merch = self.clean_merchant_name(merch)
            if self.is_valid_merchant_name(merch): return merch

        spent_time = re.compile(r"Spent[\s\S]*?\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*\n\s*([^\n]+?)(?:\s*\n|\s*Avl Limit:|\s*Avl Lmt|\s*Not you?)", re.IGNORECASE)
        match = spent_time.search(message)
        if match:
            merch = match.group(1).strip()
            merch = re.sub(r"\s+Limi$", "", merch)
            merch = re.sub(r"\s+Pay$", "", merch)
            merch = re.sub(r"\s+SUPE$", "", merch)
            merch = self.clean_merchant_name(merch)
            if self.is_valid_merchant_name(merch): return merch

        pats = [re.compile(r"UPI/[^/]+/[^/]+/([^\n]+?)(?:\s*Not you|\s*$)", re.IGNORECASE),
                re.compile(r"UPI/P2A/[^/]+/([^\n]+?)(?:\s*Not you|\s*$)", re.IGNORECASE)]
        for p in pats:
            m = p.search(message)
            if m:
                merch = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(merch): return merch

        info = re.search(r"Info\s*[-–]\s*([^.\n]+?)(?:\.\s*Chk|\s*$)", message, re.IGNORECASE)
        if info:
            val = info.group(1).strip()
            return "Salary" if "salary" in val.lower() else self.clean_merchant_name(val)

        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        ac_pats = [re.compile(r"A/c\s+no\.\s+([X\*xX]+[a-zA-Z\d]+)", re.IGNORECASE),
                   re.compile(r"Card\s+no\.\s+([X\*]*\d+)", re.IGNORECASE),
                   re.compile(r"Credit\s+Card\s+([X\*]*\d+)", re.IGNORECASE)]
        for p in ac_pats:
            m = p.search(message)
            if m:
                s = m.group(1)
                chars = "".join(filter(str.isalnum, s))
                if any(c.islower() for c in chars):
                    return chars[-4:].lower() if len(chars) >= 4 else chars.lower()
                digits = "".join(filter(str.isdigit, s))
                return digits[-4:] if len(digits) >= 4 else digits
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"UPI/[^/]+/([0-9]+)", message, re.IGNORECASE)
        if m: return m.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        lower = message.lower()
        if "payment" in lower and "has been received" in lower and "towards your axis bank" in lower:
            return False
        return super().is_transaction_message(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        lower = message.lower()
        if "avl limit" in lower or "avl lmt" in lower: return TransactionType.CREDIT
        if (("credit card" in lower or " cc " in lower) and ("debited" in lower or "spent" in lower)):
            return TransactionType.CREDIT
        return super().extract_transaction_type(message)

    def extract_available_limit(self, message: str) -> Optional[Decimal]:
        pats = [re.compile(r"Avl\s+Limit:?\s*INR\s+([0-9,]+(?:\.\d{2})?)", re.IGNORECASE),
                re.compile(r"Avl\s+Lmt\s+INR\s+([0-9,]+(?:\.\d{2})?)", re.IGNORECASE),
                re.compile(r"Available\s+limit:?\s*INR\s+([0-9,]+(?:\.\d{2})?)", re.IGNORECASE)]
        for p in pats:
            m = p.search(message)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_available_limit(message)
