import re
from decimal import Decimal, InvalidOperation
from typing import Optional, List
import unicodedata
from dataclasses import dataclass

from base_indian_bank_parser import BaseIndianBankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class SBIBankParser(BaseIndianBankParser):
    """
    Parser for State Bank of India (SBI) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "State Bank of India"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if any(k in up for k in ["SBI", "SBIINB", "SBIUPI", "SBICRD", "ATMSBI", "SBI CARDS"]) or up in ["SBIBK", "SBIBNK"]:
            return True
        pats = [r"^[A-Z]{2}-SBIBK-S$", r"^[A-Z]{2}-SBIBK-[TPG]$", r"^[A-Z]{2}-SBIBK$", r"^[A-Z]{2}-SBI$"]
        return any(re.match(p, up) for p in pats)

    def is_credit_card_message(self, sender: str, message: str) -> bool:
        up_s = sender.upper()
        return "SBICRD" in up_s or "SBI CARDS" in up_s or "credit card" in message.lower()

    def extract_credit_card_last4(self, message: str) -> Optional[str]:
        pats = [r"ending\s+with\s+(\d{4})", r"ending\s+(\d{4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return None

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        norm = self.normalize_unicode_text(sms_body)
        parsed = super().parse(norm, sender, timestamp)
        if not parsed: return None
        
        if self.is_credit_card_message(sender, norm):
            card_last4 = self.extract_credit_card_last4(norm) or parsed.accountLast4
            limit = self.extract_available_limit(norm) or parsed.creditLimit
            
            low = norm.lower()
            if "payment of" in low and "credited to your sbi credit card" in low:
                tt = TransactionType.INCOME
            elif "spent on" in low or "spent" in low:
                tt = TransactionType.CREDIT
            else:
                tt = TransactionType.CREDIT
                
            mer = None
            if "via bbps" in low: mer = "BBPS Payment"
            else: mer = self.extract_credit_card_merchant(norm) or parsed.merchant
            
            parsed.accountLast4 = card_last4
            parsed.type = tt
            parsed.merchant = mer or parsed.merchant
            parsed.creditLimit = limit
            parsed.isFromCard = True
            
        return parsed

    def normalize_unicode_text(self, text: str) -> str:
        norm = unicodedata.normalize('NFKD', text)
        return "".join([c for c in norm if ord(c) < 128])

    def extract_credit_card_merchant(self, message: str) -> Optional[str]:
        m = re.search(r"at\s+([A-Za-z0-9\s&._-]+?)\s+on\s+\d", message, re.I)
        if m:
            mer = self.clean_merchant_name(m.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
        return None

    def extract_available_limit(self, message: str) -> Optional[Decimal]:
        pats = [r"available\s+limit\s+is\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Your\s+available\s+limit\s+is\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_available_limit(message)

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"transaction\s+number\s+\d+\s+for\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"payment\s+of\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Rs\.?\s*([0-9,]+(?:\.\d{2})?)\s+spent",
                r"debited\s+by\s+(\d+(?:,\d{3})*(?:\.\d{1,2})?)",
                r"credited\s+by\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)",
                r"Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s+(?:has\s+been\s+)?debited",
                r"INR\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s+(?:has\s+been\s+)?debited",
                r"Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s+(?:has\s+been\s+)?credited",
                r"INR\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s+(?:has\s+been\s+)?credited",
                r"withdrawn\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"transferred\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"paid\s+to\s+[\w.-]+@[\w]+\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"ATM\s+withdrawal\s+of\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"Yono\s+Cash\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if "withdrawn" in low or "transferred" in low or "paid to" in low or "atm withdrawal" in low or "by sbi debit card" in low:
            return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m1 = re.search(r"done\s+at\s+([^.\n]+?)(?:\s+on\s+|$)", message, re.I)
        if m1:
            loc = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(loc): return loc
            
        m2 = re.search(r"trf\s+to\s+([^.\n]+?)(?:\s+Ref|\s+ref|$)", message, re.I)
        if m2:
            mer = self.clean_merchant_name(m2.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m3 = re.search(r"transfer\s+from\s+([^.\n]+?)(?:\s+Ref|\s+ref|$)", message, re.I)
        if m3:
            mer = self.clean_merchant_name(m3.group(1).strip())
            if self.is_valid_merchant_name(mer): return mer
            
        m4 = re.search(r"paid\s+to\s+([\w.-]+)@[\w]+", message, re.I)
        if m4:
            mer = self.clean_merchant_name(m4.group(1))
            if self.is_valid_merchant_name(mer): return mer
            
        m5 = re.search(r"w/d@SBI\s+ATM\s+([A-Z0-9]+)", message, re.I)
        if m5: return f"YONO Cash ATM - {m5.group(1)}"
        
        m6 = re.search(r"ATM\s+(?:withdrawal\s+)?(?:at\s+)?([^.\n]+?)(?:\s+on|\s+Avl)", message, re.I)
        if m6:
            loc = self.clean_merchant_name(m6.group(1))
            if self.is_valid_merchant_name(loc): return f"ATM - {loc}"
            
        m7 = re.search(r"(?:NEFT|IMPS|RTGS)[^:]*:\s*([^.\n]+?)(?:\s+Ref|\s+on|$)", message, re.I)
        if m7:
            mer = self.clean_merchant_name(m7.group(1))
            if self.is_valid_merchant_name(mer): return mer
            
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"by\s+SBI\s+Debit\s+Card\s+([\w\-]+)", message, re.I)
        if m1:
            inf = m1.group(1)
            if re.match(r"^\d{4}$", inf): return inf
            dig = "".join(filter(str.isdigit, inf))
            return dig[-4:] if len(dig) >= 4 else inf
            
        m2 = re.search(r"A/c\s+([X\*]*\d+)", message, re.I)
        if m2:
            dig = "".join(filter(str.isdigit, m2.group(1)))
            return dig[-4:] if len(dig) >= 4 else dig
            
        m3 = re.search(r"A/c\s+ending\s+(\d{4})", message, re.I)
        if m3: return m3.group(1)
        
        m4 = re.search(r"a/c\s+no\.?\s+(?:XX|X\*+)?(\d{4})", message, re.I)
        if m4: return m4.group(1)
        
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Your\s+updated\s+available\s+balance\s+is\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"Avl\s+Bal\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"Available\s+Balance:?\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"Bal:?\s+Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"transaction\s+number\s+([\w\-]+)",
                r"Ref\s+No\.?\s*(\w+)",
                r"Txn#\s*(\w+)",
                r"transaction\s+ID:?\s*(\w+)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_reference(message)

    def is_transaction_message(self, message: str) -> bool:
        norm = self.normalize_unicode_text(message)
        low = norm.lower()
        if "e-statement of sbi credit card" in low: return False
        if "is due for" in low: return False
        if any(k in low for k in ["sbi card application", "process your app.no", "track your application status"]): return False
        if self.is_emi_mandate_notification(norm) or self.is_upi_mandate_notification(norm): return False
        if "by sbi debit card" in low: return True
        if "spent" in low and "credit card" in low: return True
        return super().is_transaction_message(norm)

    def is_emi_mandate_notification(self, message: str) -> bool:
        low = message.lower()
        return "e-mandate" in low or "e mandate" in low

    def is_upi_mandate_notification(self, message: str) -> bool:
        low = message.lower()
        return "upi-mandate" in low or "upi mandate" in low or ("mandate" in low and "created" in low and "upi" in low)

    def parse_upi_mandate_subscription(self, message: str):
        if not self.is_upi_mandate_notification(message) and not self.is_emi_mandate_notification(message): return None
        
        pats_amt = [r"Rs\.?\s*([0-9,]+(?:\.\d{2})?)", r"INR\s*([0-9,]+(?:\.\d{2})?)"]
        amt = None
        for p in pats_amt:
            m = re.search(p, message, re.I)
            if m:
                try: amt = Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
            if amt: break
        if not amt: return None
        
        mer = "Unknown Subscription"
        pats_mer = [r"towards\s+([^.\n]+?)(?:\s+from|\s+A/c|\s+UMRN|\s+ID:|\s+Alert:|\s*\.||$)",
                    r"for\s+([^.\n]+?)(?:\s+ID:|\s+Act:|\s*\.||$)",
                    r"mandate\s+created\s+for\s+([^.\n]+?)(?:\s+UMN|\s+of|\s*\.||$)"]
        for p in pats_mer:
            m = re.search(p, message, re.I)
            if m:
                cm = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(cm):
                    mer = cm
                    break
                    
        pats_dt = [r"on\s+(\d{2}-\w{3}-\d{2,4})", r"date[:\s]+(\d{2}/\d{2}/\d{2,4})", r"(\d{2}-\d{2}-\d{4})"]
        dt = None
        for p in pats_dt:
            m = re.search(p, message, re.I)
            if m:
                dt = m.group(1)
                break
                
        umn = None
        m_umn = re.search(r"UMN[:\s]+([^.\s]+)", message, re.I)
        if m_umn: umn = m_umn.group(1)
        
        return {"amount": amt, "nextDeductionDate": dt, "merchant": mer, "umn": umn}
