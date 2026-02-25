import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class ICICIBankParser(BaseIndianBankParser):
    """
    Parser for ICICI Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "ICICI Bank"

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
            account_last4=self.extract_account_last4(sms_body),
            balance=self.extract_balance(sms_body),
            credit_limit=avail_limit,
            sms_body=sms_body,
            sender=sender,
            timestamp=timestamp,
            bank_name=self.get_bank_name(),
            is_from_card=self.detect_is_card(sms_body),
            currency=currency
        )

    def _extract_currency(self, message: str) -> Optional[str]:
        m = re.search(r"([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?\s+spent", message, re.I)
        if m:
            cur = m.group(1).upper()
            if len(cur) == 3 and not re.match(r"^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$", cur):
                return cur
        return None

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        if "ICICI" in norm or "ICICIB" in norm: return True
        pats = [r"^[A-Z]{2}-ICICIB-S$", r"^[A-Z]{2}-ICICI-S$", r"^[A-Z]{2}-ICICIB-[TPG]$", r"^[A-Z]{2}-ICICIB$", r"^[A-Z]{2}-ICICI$"]
        if any(re.match(p, norm) for p in pats): return True
        return norm in ["ICICIB", "ICICIBANK"]

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"[A-Z]{3}\s+([0-9,]+(?:\.\d{2})?)\s+spent",
                r"(?:Rs\.?|INR)\s+([0-9,]+(?:\.\d{2})?)\s+spent",
                r"debited\s+with\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"debited\s+for\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"credited\s+with\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"credited:\s*Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if re.search(r"Info\s+INF\*[^*]+\*[^*]*SAL[^.]*", message, re.I): return "Salary"
        if any(kw in low for kw in ["nfscash wdl", "nfs cash wdl", "nfs*cash wdl", "cash wdl", "nfscash"]): return "Cash Withdrawal"
        
        m1 = re.search(r"on\s+\d{1,2}-\w{3}-\d{2}\s+(?:at|on)\s+([^.]+?)(?:\.|\s+Avl|$)", message, re.I)
        if m1:
            merch = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
            
        m2 = re.search(r"Info\s+(?:ACH|NACH)\*([^*]+)\*", message, re.I)
        if m2: return f"{self.clean_merchant_name(m2.group(1).strip())} Dividend"
        
        m3 = re.search(r"towards\s+([^.\n]+?)\s+for", message, re.I)
        if m3:
            merch = self.clean_merchant_name(m3.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
            
        m4 = re.search(r"from\s+([^.\n]+?)\.\s*UPI", message, re.I)
        if m4:
            merch = self.clean_merchant_name(m4.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
            
        m5 = re.search(r";\s*([^.\n]+?)\s+credited\.\s*UPI", message, re.I)
        if m5:
            merch = self.clean_merchant_name(m5.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch
            
        if "info by cash" in low: return "Cash Deposit"
        if "autopay" in low:
            if "google play" in low: return "Google Play Store"
            if "netflix" in low: return "Netflix"
            if "spotify" in low: return "Spotify"
            if "amazon prime" in low: return "Amazon Prime"
            if "disney" in low or "hotstar" in low: return "Disney+ Hotstar"
            if "youtube" in low: return "YouTube Premium"
            return "AutoPay Subscription"
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"ICICI\s+Bank\s+Card\s+[X\*]*(\d+)", message, re.I)
        if m1:
            val = m1.group(1)
            return val[-4:] if len(val) >= 4 else val
            
        m2 = re.search(r"ICICI\s+Bank\s+Credit\s+Card\s+[X\*]*(\d{4})", message, re.I)
        if m2: return m2.group(1)
        
        m3 = re.search(r"ICICI\s+Bank\s+Account\s+([X\*]*\d+)", message, re.I)
        if m3:
            d = "".join(filter(str.isdigit, m3.group(1)))
            return d[-4:] if len(d) >= 4 else (d if d else None)
            
        m4 = re.search(r"ICICI\s+Bank\s+Acct\s+[X\*]*(\d{3,4})", message, re.I)
        if m4: return m4.group(1)[-4:]
        m5 = re.search(r"ICICI\s+Bank\s+Acc\s+[X\*]*(\d{3,4})", message, re.I)
        if m5: return m5.group(1)[-4:]
        
        m6 = re.search(r"Acct\s+XX(\d{3,4})(?:\s|$|[,;.])", message, re.I)
        if m6: return m6.group(1)[-4:]
        m7 = re.search(r"Acc\s+XX(\d{3,4})(?:\s|$|[,;.])", message, re.I)
        if m7: return m7.group(1)[-4:]
        m8 = re.search(r"Acct\s+\*+(\d{3,4})(?:\s|$|[,;.])", message, re.I)
        if m8: return m8.group(1)[-4:]
        
        return None

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Available\s+Balance\s+is\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Av[lb]\s+Bal\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Updated\s+Bal[:\s]+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"RRN\s+([A-Za-z0-9]+)", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"UPI:([A-Za-z0-9]+)", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"transaction\s+reference\s+no\.?([A-Z0-9]+)", message, re.I)
        if m3: return m3.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "cash deposit transaction" in low and "has been completed" in low: return False
        if "is due by" in low: return False
        if "will be debited" in low: return False
        if "has been received on your icici bank credit card" in low: return False
        
        kw = ["debited with", "debited for", "credited with", "credited:", "autopay", "your account has been", "inr", "spent using"]
        return any(k in low for k in kw) or super().is_transaction_message(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if ("icici bank credit card" in low or ("icici bank card" in low and "spent" in low)) and \
           ("spent" in low or "debited" in low):
            return TransactionType.CREDIT
        if "info by cash" in low: return TransactionType.INCOME
        return super().extract_transaction_type(message)
