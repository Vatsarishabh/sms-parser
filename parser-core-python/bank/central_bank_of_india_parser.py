import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class CentralBankOfIndiaParser(BankParser):
    """
    Parser for Central Bank of India (CBoI) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Central Bank of India"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return any(k in norm for k in ["CENTBK", "CBOI", "CENTRALBANK", "CENTRAL"]) or \
               re.match(r"^[A-Z]{2}-(CENTBK|CBOI)-[A-Z]$", norm)

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        if not self.can_handle(sender): return None
        if not self.is_transaction_message(sms_body): return None

        amount = self.extract_amount(sms_body)
        if amount is None: return None
        
        transaction_type = self.extract_transaction_type(sms_body)
        if transaction_type is None: return None
        
        merchant = self.extract_merchant(sms_body, sender) or "Unknown"

        return ParsedTransaction(
            amount=amount,
            type=transaction_type,
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
        pats = [re.compile(r"(?:Credited|Debited)\s+by\s+Rs\.?\s*([\d,]+(?:\.\d{2})?)", re.IGNORE_CASE),
                re.compile(r"Rs\.?\s*([\d,]+(?:\.\d{2})?)\s+(?:credited|debited)", re.IGNORE_CASE)]
        for p in pats:
            m = p.search(message)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        # Pattern 1: "By.NAME" or "By NAME"
        m = re.search(r"By[.\s]+(.+?)(?:-CBoI|-CBOI|-CENTBK|$)", message, re.IGNORE_CASE)
        if m:
            merch = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch

        # Pattern 2: "from [NAME]"
        m = re.search(r"from\s+([A-Z0-9]+|[^\s]+?)(?:\s+via|\s+Ref|\s+\.|$)", message, re.IGNORE_CASE)
        if m:
            merch = m.group(1).strip()
            if "X" in merch: return "UPI Transfer"
            return self.clean_merchant_name(merch)

        # Pattern 3: "to [NAME]"
        m = re.search(r"to\s+([^\s]+?)(?:\s+via|\s+Ref|\s+\.|$)", message, re.IGNORE_CASE)
        if m:
            merch = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch

        if "via upi" in message.lower():
            if "credited" in message.lower(): return "UPI Credit"
            if "debited" in message.lower(): return "UPI Payment"

        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"account\s+[X*]*(\d{4})", message, re.IGNORE_CASE)
        if m: return m.group(1)
        m = re.search(r"A/C\s+ending\s+[X*]*(\d{4})", message, re.IGNORE_CASE)
        if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [re.compile(r"Total\s+Bal\s+Rs\.?\s*([\d,]+(?:\.\d{2})?)\s+(CR|DR)", re.IGNORE_CASE),
                re.compile(r"Clear\s+Bal\s+Rs\.?\s*([\d,]+(?:\.\d{2})?)\s+(CR|DR)", re.IGNORE_CASE)]
        for p in pats:
            m = p.search(message)
            if m:
                try:
                    val = Decimal(m.group(1).replace(",", ""))
                    return -val if m.group(2).upper() == "DR" else val
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r"Ref\s+No\.?\s*(\w+)", message, re.IGNORE_CASE)
        if m: return m.group(1)
        return super().extract_reference(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(kw in low for kw in ["credited", "deposited", "received"]): return TransactionType.INCOME
        if any(kw in low for kw in ["debited", "withdrawn", "paid"]): return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if ("credited by" in low or "debited by" in low) and "bal" in low: return True
        if "-cboi" in low:
            return "credited" in low or "debited" in low
        return super().is_transaction_message(message)
