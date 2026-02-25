import re
from decimal import Decimal, InvalidOperation
from typing import Optional
from datetime import datetime

from base_indian_bank_parser import BaseIndianBankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class SouthIndianBankParser(BaseIndianBankParser):
    """
    South Indian Bank specific parser.
    """

    def get_bank_name(self) -> str:
        return "South Indian Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        sibs = {"SIBSMS", "AD-SIBSMS", "CP-SIBSMS", "SIBSMS-S", "AD-SIBSMS-S", "CP-SIBSMS-S", "SOUTHINDIANBANK", "SIBBANK"}
        if up in sibs or "SIBSMS" in up or "SIBBANK" in up: return True
        return up.startswith("AD-SIB") or up.startswith("CP-SIB") or up.startswith("VM-SIB")

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        if not self.is_transaction_message(sms_body): return None
        
        amt = self.extract_amount(sms_body)
        if amt is None: return None
        
        tt = self.extract_transaction_type(sms_body)
        if tt is None: return None
        
        mer = self.extract_merchant(sms_body, sender) or "Unknown"
        ref = self.extract_reference(sms_body)
        ac = self.extract_account_last4(sms_body)
        bal = self.extract_balance(sms_body)
        
        return ParsedTransaction(
            amount=amt,
            type=tt,
            merchant=mer,
            reference=ref,
            accountLast4=ac,
            balance=bal,
            smsBody=sms_body,
            sender=sender,
            timestamp=timestamp,
            bankName=self.get_bank_name()
        )

    def extract_amount(self, message: str) -> Optional[Decimal]:
        m = re.search(r"(?:Rs\.?|INR)\s*([0-9,]+(?:\.\d{2})?)", message, re.I)
        if m:
            try: return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "imps" in low and "info:" in low:
            m = re.search(r"Info:\s*IMPS/[^/]+/[^/]+/([^.]+)", message, re.I)
            if m: return self.clean_merchant_name(m.group(1).strip())
            
        if "upi" in low:
            m = re.search(r"Info:UPI/[^/]+/[^/]+/([^/]+?)\s+on", message, re.I)
            if m: return self.clean_merchant_name(m.group(1).strip())
            
            pref = message[:200]
            m2 = re.search(r"to\s+([^,\s]+@[^\s,]+)", pref, re.I)
            if m2: return self.clean_merchant_name(m2.group(1).strip())
            
            if "credit" in low:
                m3 = re.search(r"from\s+([^,\s]+@[^\s,]+)", pref, re.I)
                if m3: return self.clean_merchant_name(m3.group(1).strip())
                return "UPI Credit"
            return "UPI Transaction"
            
        if ("debit" in low or "credit" in low) and "upi" not in low:
            m = re.search(r"(?:DEBIT|CREDIT)[:\s]*Rs\.?\s*[0-9,]+(?:\.\d{2})?\s+([A-Z\s]+?)\s+(?:Bal|Available)", message, re.I)
            if m:
                mer = m.group(1).strip()
                if len(mer) > 2: return self.clean_merchant_name(mer)
                
        if "atm" in low or "withdrawn" in low: return "ATM"
        
        if "card" in low:
            m = re.search(r"at\s+([^,\n]+?)(?:\s+on|\s*,|$)", message, re.I)
            if m: return self.clean_merchant_name(m.group(1).strip())
            
        return super().extract_merchant(message, sender)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(k in low for k in ["debit", "withdrawn", "spent", "purchase", "paid", "transfer to"]):
            return TransactionType.EXPENSE
        if any(k in low for k in ["credit", "deposited", "received", "refund", "transfer from", "cashback"]):
            return TransactionType.INCOME
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        if "imps" in message.lower() and "info:" in message.lower():
            m = re.search(r"Info:\s*IMPS/[^/]+/([^/]+)/", message, re.I)
            if m: return m.group(1).strip()
            
        m2 = re.search(r"RRN[:\s]*(\d{12})", message, re.I)
        if m2: return m2.group(1).strip()
        
        m3 = re.search(r"Ref(?:erence)?[:\s]*([A-Z0-9]+)", message, re.I)
        if m3: return m3.group(1).strip()
        
        return super().extract_reference(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"A/c\s+[X*]*(\d{4})", r"Account\s+[X*]*(\d{4})", r"from\s+[X*]*(\d{4})", r"to\s+[X*]*(\d{4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Final\s+balance\s+is\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Bal(?:ance)?[:\s]*Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Available\s+Bal(?:ance)?[:\s]*Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Avl\s+Bal[:\s]*Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "one time password", "verification code", "offer", "discount"]): return False
        if "upi auto pay" in low and "is scheduled on" in low: return False
        kw = ["debit", "credit", "withdrawn", "deposited", "spent", "received", "transferred", "paid", "purchase", "refund", "cashback", "upi"]
        return any(k in low for k in kw)
