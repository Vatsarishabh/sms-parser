import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType

class BankOfIndiaParser(BaseIndianBankParser):
    """
    Parser for Bank of India (BOI) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Bank of India"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        if norm in ["BOIIND", "BOIBNK"]: return True
        pats = [r"^[A-Z]{2}-BOIIND-[ST]$", r"^[A-Z]{2}-BOIBNK-[ST]$", r"^[A-Z]{2}-BOI-[ST]$",
                r"^[A-Z]{2}-BOIIND$", r"^[A-Z]{2}-BOIBNK$", r"^[A-Z]{2}-BOI$",
                r"^BK-BOIIND.*$", r"^JD-BOIIND.*$"]
        return any(re.match(p, norm) for p in pats)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s+(?:debited|credited)",
                r"INR\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s+(?:debited|credited)",
                r"withdrawn\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "deposited in your account" in low or ("cash" in low and "deposited" in low):
            return TransactionType.INCOME
        if self.is_investment_transaction(low): return TransactionType.INVESTMENT
        if "mandate" in low and any(k in low for k in ["mutual fund", "iccl", "groww", "zerodha", "kuvera", "paytm money"]):
            return TransactionType.INVESTMENT
        if "debited" in low and "and credited to" in low: return TransactionType.EXPENSE
        if "credited" in low and "and debited from" in low: return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "cash acceptor machine" in low or ("cash" in low and "deposited" in low):
            return "Cash Deposit"
            
        if "mandate" in low and "towards" in low:
            m_via = re.search(r"via\s+([A-Za-z0-9]+)", message, re.I)
            if m_via and self.is_valid_merchant_name(m_via.group(1).strip()):
                return self.clean_merchant_name(m_via.group(1).strip())
            m_tow = re.search(r"towards\s+([^,\n]+?)(?:\s+for|\s*,|$)", message, re.I)
            if m_tow:
                mi = m_tow.group(1).strip()
                mer = re.sub(r"\s*-\s*Autopa.*$", "", mi, flags=re.I).strip()
                if self.is_valid_merchant_name(mer): return self.clean_merchant_name(mer)
                
        m1 = re.search(r"credited\s+to\s+([^.\n]+?)(?:\s+via|\s+Ref|\s+on|$)", message, re.I)
        if m1 and self.is_valid_merchant_name(m1.group(1).strip()): return self.clean_merchant_name(m1.group(1).strip())
        
        m2 = re.search(r"debited\s+from\s+([^.\n]+?)(?:\s+via|\s+Ref|\s+on|$)", message, re.I)
        if m2 and self.is_valid_merchant_name(m2.group(1).strip()): return self.clean_merchant_name(m2.group(1).strip())
        
        if "atm" in low or "withdrawn" in low:
            m = re.search(r"(?:ATM|withdrawn)\s+(?:at\s+)?([^.\n]+?)(?:\s+on|\s+Ref|$)", message, re.I)
            if m and self.is_valid_merchant_name(m.group(1).strip()):
                return f"ATM - {self.clean_merchant_name(m.group(1).strip())}"
            return "ATM"
            
        if "mandate" not in low:
            m_tow = re.search(r"towards\s+([^.\n]+?)(?:\s+via|\s+Ref|\s+on|$)", message, re.I)
            if m_tow and self.is_valid_merchant_name(m_tow.group(1).strip()): return self.clean_merchant_name(m_tow.group(1).strip())
            
        for p in [r"to\s+([^.\n]+?)(?:\s+via|\s+Ref|\s+on|$)", r"from\s+([^.\n]+?)(?:\s+via|\s+Ref|\s+on|$)"]:
            m = re.search(p, message, re.I)
            if m and self.is_valid_merchant_name(m.group(1).strip()): return self.clean_merchant_name(m.group(1).strip())
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"A/c\s*(?:XX|X\*+)?(\d{4})", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"(?:Account|A/c)\s+ending\s+(\d{4})", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"A/c\s+No\.?\s*(?:XX|X\*+)?(\d{4})", message, re.I)
        if m3: return m3.group(1)
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"Ref\s+No\.?\s*(\d+)", r"Reference[:\s]+(\w+)", r"Txn\s*(?:ID|#)[:\s]*(\w+)", r"UPI[:\s]+(\d+)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_reference(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Bal[:\s]+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"Available\s+Balance[:\s]+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"Avl\s+Bal[:\s]+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if "will be" in low: return False
        if "call" in low and "if not done by you" in low:
            if any(k in low for k in ["debited", "credited", "withdrawn", "transferred"]): return True
        if any(k in low for k in ["otp", "one time password", "verification code"]): return False
        if any(k in low for k in ["offer", "discount", "cashback offer", "win "]): return False
        return super().is_transaction_message(message)
