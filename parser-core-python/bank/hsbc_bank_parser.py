import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class HSBCBankParser(BankParser):
    """
    Parser for HSBC Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "HSBC Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return "HSBC" in norm or "HSBCIN" in norm or \
               re.match(r"^[A-Z]{2}-HSBCIN-[A-Z]$", norm) or \
               re.match(r"^[A-Z]{2}-HSBC-[A-Z]$", norm)

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        if not self.can_handle(sender): return None
        if not self.is_transaction_message(sms_body): return None

        amount = self.extract_amount(sms_body)
        if amount is None: return None
        
        ttype = self.extract_transaction_type(sms_body)
        if ttype is None: return None
        
        merchant = self.extract_merchant(sms_body, sender) or "Unknown"

        return ParsedTransaction(
            amount=amount,
            type=ttype,
            merchant=merchant,
            accountLast4=self.extract_account_last4(sms_body),
            balance=self.extract_balance(sms_body),
            reference=self.extract_reference(sms_body),
            smsBody=sms_body,
            sender=sender,
            timestamp=timestamp,
            bankName=self.get_bank_name()
        )

    def extract_amount(self, message: str) -> Optional[Decimal]:
        p1 = re.search(r"INR\s+([\d,]+(?:\.\d{2})?)\s+is\s+(?:paid|credited|debited)", message, re.I)
        if p1:
            try: return Decimal(p1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        p2 = re.search(r"for\s+INR\s+([\d,]+(?:\.\d{2})?)\s+on", message, re.I)
        if p2:
            try: return Decimal(p2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        p3 = re.search(r"for\s+INR\s+([\d,]+(?:\.\d{2})?)(?:\s|$|\.)", message, re.I)
        if p3:
            try: return Decimal(p3.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        # Beneficiary name
        m0 = re.search(r"credited\s+to\s+the\s+\w+\s+A/c\s+[X\d]+\s+of\s+(.+?)\s+on\s+", message, re.I)
        if m0:
            name = self.clean_merchant_name(m0.group(1).strip())
            if self.is_valid_merchant_name(name): return name
            
        m1 = re.search(r"as\s+(?:NEFT|RTGS|IMPS)\s+from\s+(.+?)\s+\.", message, re.I)
        if m1:
            name = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(name): return name
            
        m2 = re.search(r"at\s+([^.]+?)\s*\.", message, re.I)
        if m2:
            name = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(name): return name
            
        m3 = re.search(r"used\s+at\s+([^\s]+)\s+for\s+INR", message, re.I)
        if m3:
            name = self.clean_merchant_name(m3.group(1).strip())
            if self.is_valid_merchant_name(name): return name
            
        m4 = re.search(r"to\s+([^.]+?)\s+on\s+\d", message, re.I)
        if m4:
            name = self.clean_merchant_name(m4.group(1).strip())
            if self.is_valid_merchant_name(name): return name
            
        m5 = re.search(r"from\s+([^.]+?)(?:\s+on\s+|\s+with\s+|$)", message, re.I)
        if m5:
            name = self.clean_merchant_name(m5.group(1).strip())
            if self.is_valid_merchant_name(name): return name
            
        return super().extract_merchant(message, sender)

    def clean_merchant_name(self, merchant: str) -> str:
        cleaned = super().clean_merchant_name(merchant)
        cleaned = re.sub(r"\s+for\s+INR\s+[\d,]+(?:\.\d{2})?$", "", cleaned, flags=re.I)
        return cleaned.strip()

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"A/c\s+\d+-\d+\*+-(\d+)", message, re.I)
        if m1: return m1.group(1).rjust(4, '0')
        
        m2 = re.search(r"Debit\s+Card\s+[X*]+(\d+[xX]*)", message, re.I)
        if m2:
            val = m2.group(1)
            return val[-4:].lower() if len(val) >= 4 else val.lower()
            
        m3 = re.search(r"credit\s*card\s+[xX*]+(\d{4})", message, re.I)
        if m3: return m3.group(1)
        
        m4 = re.search(r"account\s+[X*]+(\d{4})", message, re.I)
        if m4: return m4.group(1)
        
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"with\s+UTR\s+(\w+)", message, re.I)
        if m: return m.group(1)
        m = re.search(r"with\s+ref\s+(\w+)", message, re.I)
        if m: return m.group(1)
        return super().extract_reference(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        m1 = re.search(r"(?:Your\s+)?Avl\s+Bal\s+is\s+INR\s+([\d,]+(?:\.\d{2})?)", message, re.I)
        if m1:
            try: return Decimal(m1.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        m2 = re.search(r"available\s+bal\s+is\s+INR\s+([\d,]+(?:\.\d{2})?)", message, re.I)
        if m2:
            try: return Decimal(m2.group(1).replace(",", ""))
            except (InvalidOperation, ValueError): pass
            
        return super().extract_balance(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "debit card" in low and ("thank you for using" in low or "for inr" in low): return TransactionType.EXPENSE
        if "creditcard" in low or "credit card" in low: return TransactionType.CREDIT
        
        if self._is_outgoing_neft(message): return TransactionType.TRANSFER
        
        if any(k in low for k in ["is paid from", "is debited"]): return TransactionType.EXPENSE
        if any(k in low for k in ["is credited to", "is credited with", "deposited"]): return TransactionType.INCOME
        
        return super().extract_transaction_type(message)

    def _is_outgoing_neft(self, message: str) -> bool:
        low = message.lower()
        if not any(k in low for k in ["neft", "rtgs", "imps"]): return False
        m = re.search(r"credited\s+to\s+the\s+(\w+)\s+A/c", message, re.I)
        if m and m.group(1).upper() != "HSBC": return True
        if "credited to" in low and re.search(r"A/c\s+[X\d]+\s+of\s+\w+", message, re.I): return True
        return False

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "otp is" in low or "otp valid for" in low: return False
        kw = ["is paid from", "is credited to", "is debited", "used at", "thank you for using", "for inr", "account"]
        return any(k in low for k in kw) or super().is_transaction_message(message)
