import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from uae_bank_parser import UAEBankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class MashreqBankParser(UAEBankParser):
    """
    Parser for Mashreq Bank - UAE.
    """

    def get_bank_name(self) -> str:
        return "Mashreq Bank"

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        if not self.is_transaction_message(sms_body): return None
        
        amt = self.extract_amount(sms_body)
        if amt is None: return None
        
        type = self.extract_transaction_type(sms_body)
        if type is None: return None
        
        cur = self.extract_currency(sms_body) or "AED"
        
        limit = None
        if type == TransactionType.CREDIT:
            limit = self.extract_available_limit(sms_body)
            
        return ParsedTransaction(
            amount=amt,
            type=type,
            merchant=self.extract_merchant(sms_body, sender),
            reference=self.extract_reference(sms_body),
            accountLast4=self.extract_account_last4(sms_body),
            balance=self.extract_balance(sms_body),
            creditLimit=limit,
            smsBody=sms_body,
            sender=sender,
            timestamp=timestamp,
            bankName=self.get_bank_name(),
            isFromCard=self.detect_is_card(sms_body),
            currency=cur
        )

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if up == "MASHREQ" or "MASHREQ" in up or up == "MSHREQ": return True
        pats = [r"^[A-Z]{2}-MASHREQ-[A-Z]$", r"^[A-Z]{2}-MSHREQ-[A-Z]$"]
        return any(re.match(p, up) for p in pats)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        if "debit card" in message.lower() or "credit card" in message.lower():
            m = re.search(r"at\s+([^,\n]+?)\s+on\s+\d{1,2}-[A-Z]{3}-\d{4}", message, re.I)
            if m: return self.clean_merchant_name(m.group(1).strip())
            
        low = message.lower()
        if "atm" in low and "withdrawn" in low: return "ATM Withdrawal"
        if "transfer" in low: return "Transfer"
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"Card ending\s+([X\d]{4})", r"card\s+(?:no\.|number)\s+([X\d]{4})", r"account\s+(?:no\.|number)?\s*([X\d]{4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                s = m.group(1).replace("X", "").replace("x", "")
                if any(c.isdigit() for c in s): return s
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Available Balance is\s+([A-Z]{3})\s+([X0-9,]+(?:\.\d{2})?)",
                r"Avl\.?\s*Bal\.?\s+([A-Z]{3})\s+([X0-9,]+(?:\.\d{2})?)",
                r"Balance:?\s+([A-Z]{3})\s+([X0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                s = m.group(2).replace(",", "").replace("X", "0").replace("x", "0")
                try: return Decimal(s)
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"on\s+(\d{1,2}-[A-Z]{3}-\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)",
                r"(\d{1,2}-[A-Z]{3}-\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_reference(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "debit card" in low and re.search(r"for\s+[A-Z]{3}\s+[0-9,]+", message, re.I): return TransactionType.EXPENSE
        if "credit card" in low and re.search(r"for\s+[A-Z]{3}\s+[0-9,]+", message, re.I): return TransactionType.CREDIT
        if "atm" in low and "withdrawn" in low: return TransactionType.EXPENSE
        if "atm" in low and "deposited" in low: return TransactionType.INCOME
        if "transfer" in low: return TransactionType.TRANSFER
        if "credited" in low: return TransactionType.INCOME
        if "debited" in low: return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def detect_is_card(self, message: str) -> bool:
        low = message.lower()
        kw = ["neo visa debit card", "neo debit card", "debit card card ending", "credit card card ending", "card ending", "mashreq card"]
        return any(k in low for k in kw) or super().detect_is_card(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        non = ["otp", "one time password", "verification code", "do not share", "activation", "has been blocked", "has been activated", "card request", "card application", "limit change", "pin change", "failed transaction", "transaction declined", "insufficient balance"]
        if any(k in low for k in non): return False
        kw = ["thank you for using", "neo visa debit card", "neo debit card", "debit card card ending", "credit card card ending", "available balance is"]
        return any(k in low for k in kw) or super().is_transaction_message(message)

    def extract_currency(self, message: str) -> Optional[str]:
        pats = [r"for\s+([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?",
                r"of\s+([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?",
                r"\b([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                cur = m.group(1).upper()
                if re.match(r"^[A-Z]{3}$", cur) and not re.match(r"^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$", cur, re.I):
                    return cur
        return "AED"
