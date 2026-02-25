import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class IDFCFirstBankParser(BaseIndianBankParser):
    """
    Parser for IDFC First Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "IDFC First Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return "IDFCBK" in norm or "IDFCFB" in norm or "IDFC" in norm

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        if not self.is_transaction_message(sms_body): return None

        amount = self.extract_amount(sms_body)
        if amount is None: return None

        ttype = self.extract_transaction_type(sms_body)
        if ttype is None: return None

        currency = self._extract_currency(sms_body) or "INR"
        avail_limit = self.extract_available_limit(sms_body) if ttype == TransactionType.CREDIT else None

        return ParsedTransaction(
            amount=amount,
            type=ttype,
            merchant=self.extract_merchant(sms_body, sender),
            reference=self.extract_reference(sms_body),
            accountLast4=self.extract_account_last4(sms_body),
            balance=self.extract_balance(sms_body),
            creditLimit=avail_limit,
            smsBody=sms_body,
            sender=sender,
            timestamp=timestamp,
            bankName=self.get_bank_name(),
            isFromCard=self.detect_is_card(sms_body),
            currency=currency
        )

    def _extract_currency(self, message: str) -> Optional[str]:
        m = re.search(r"([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?\s+spent", message, re.I)
        if m:
            cur = m.group(1).upper()
            if not re.match(r"^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$", cur):
                return cur
        return None

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"[A-Z]{3}\s+([0-9,]+(?:\.\d{2})?)\s+spent",
                r"Debit\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"debited\s+by\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"debited\s+by\s+INR\s*([0-9,]+(?:\.\d{2})?)",
                r"credited\s+by\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"credited\s+with\s+INR\s*([0-9,]+(?:\.\d{2})?)",
                r"credited\s+by\s+INR\s*([0-9,]+(?:\.\d{2})?)",
                r"interest\s+of\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "one time password", "verification code"]): return False
        if any(k in low for k in ["offer", "discount", "cashback offer", "win "]): return False
        if any(k in low for k in ["has requested", "payment request", "collect request", "requesting payment", "requests rs", "ignore if already paid"]): return False
        kw = ["debit", "debited", "credited", "withdrawn", "deposited", "spent", "received", "transferred", "paid", "interest"]
        return any(k in low for k in kw)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "debited" in low or "debit" in low or "spent" in low: return TransactionType.EXPENSE
        if "credited" in low: return TransactionType.INCOME
        if "withdrawn" in low or "withdrawal" in low: return TransactionType.EXPENSE
        if any(k in low for k in ["deposited", "deposit", "cash deposit"]): return TransactionType.INCOME
        if "interest" in low and ("earned" in low or "monthly interest" in low): return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "monthly interest" in low: return "Interest Credit"
        if "cash deposit" in low:
            m = re.search(r"ATM\s+(?:ID\s+)?([A-Z0-9]+)", message, re.I)
            return f"Cash Deposit - ATM {m.group(1)}" if m else "Cash Deposit"
            
        m1 = re.search(r";\s*([A-Z][A-Z0-9\s]+?)\s+credited", message, re.I)
        if m1:
            merch = self.clean_merchant_name(m1.group(1))
            if self.is_valid_merchant_name(merch): return merch

        if "upi" in low:
            m2 = re.search(r"(?:to|from|at)\s+([a-zA-Z0-9._-]+@[a-zA-Z0-9]+)", message, re.I)
            return f"UPI - {m2.group(1)}" if m2 else "UPI Transaction"
            
        if "imps" in low:
            m3 = re.search(r"mobile\s+[X]*(\d{3,4})", message, re.I)
            return f"IMPS Transfer - Mobile XXX{m3.group(1)}" if m3 else "IMPS Transfer"
            
        if "neft" in low: return "NEFT Transfer"
        if "rtgs" in low: return "RTGS Transfer"
        
        if "atm" in low:
            m4 = re.search(r"ATM\s+([A-Z]{2}\d+)", message, re.I)
            return f"ATM - {m4.group(1)}" if m4 else "ATM Transaction"
            
        m5 = re.search(r"(?:to|at|for)\s+([A-Z][A-Z0-9\s&.-]+?)(?:\s+on|\s+New|\.|\,|$)", message, re.I)
        if m5:
            merch = self.clean_merchant_name(m5.group(1))
            if self.is_valid_merchant_name(merch): return merch
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"Credit\s+Card\s+ending\s+[X]*(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"A/C\s+[X]*(\d{3,4})", message, re.I)
        if m2:
            val = m2.group(1)
            return val[-4:] if len(val) >= 4 else val
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"New\s+Bal\s*:\s*(?:INR|Rs\.?)\s*([0-9,]+(?:\.\d{2})?)",
                r"New\s+balance\s+is\s+INR\s*([0-9,]+(?:\.\d{2})?)",
                r"Updated\s+balance\s+is\s+INR\s*([0-9,]+(?:\.\d{2})?)",
                r"Available\s+balance\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"RRN\s+(\d+)", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"IMPS\s+Ref\s+no\s+(\d+)", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"UPI[:/]\s*([0-9]+)", message, re.I)
        if m3: return m3.group(1)
        m4 = re.search(r"(?:txn|transaction)\s*(?:id|ref|no)[:\s]*([A-Z0-9]+)", message, re.I)
        if m4: return m4.group(1)
        return super().extract_reference(message)
