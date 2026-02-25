import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from transaction_type import TransactionType
from compiled_patterns import CompiledPatterns

class HDFCBankParser(BaseIndianBankParser):
    """
    HDFC Bank specific parser.
    """

    def get_bank_name(self) -> str:
        return "HDFC Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if up in {"HDFCBK", "HDFCBANK", "HDFC", "HDFCB"}: return True
        return any(p.match(up) for p in CompiledPatterns.HDFC.DLT_PATTERNS)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        
        # From HDFC Bank Card xxxx At [MERCHANT] On xxx
        if "from hdfc bank card" in low and " at " in low and " on " in low:
            at_idx = message.lower().find(" at ")
            on_idx = message.lower().find(" on ")
            if at_idx != -1 and on_idx != -1 and on_idx > at_idx:
                merch = message[at_idx + 4 : on_idx].strip()
                if merch: return self.clean_merchant_name(merch)

        if "withdrawn" in low:
            m = re.search(r"At\s+\+?([^O]+?)\s+On", message, re.I)
            if m:
                loc = m.group(1).strip()
                return f"ATM at {self.clean_merchant_name(loc)}" if loc else "ATM"
            return "ATM"

        if "atm" in low: return "ATM"

        if "card" in low and " at " in low and ("block cc" in low or "block pcc" in low):
            m = re.search(r"at\s+([^@\s]+(?:@[^\s]+)?(?:\s+[^\s]+)?)(?:\s+by\s+|\s+on\s+|$)", message, re.I)
            if m:
                merch = m.group(1).strip()
                if "@" in merch:
                    vpaname = merch.split("@")[0].strip()
                    merch = vpaname[:-2] if vpaname.lower().endswith("qr") else vpaname
                if merch: return self.clean_merchant_name(merch)

        # Salary credit
        if "salary" in low and "deposited" in low:
            m = CompiledPatterns.HDFC.SALARY_PATTERN.search(message)
            if m: return self.clean_merchant_name(m.group(1).strip())
            m = CompiledPatterns.HDFC.SIMPLE_SALARY_PATTERN.search(message)
            if m:
                merch = m.group(1).strip()
                if merch and not merch.isdigit(): return self.clean_merchant_name(merch)

        if "info:" in low:
            m = CompiledPatterns.HDFC.INFO_PATTERN.search(message)
            if m:
                merch = m.group(1).strip()
                if merch and merch.upper() != "UPI": return self.clean_merchant_name(merch)

        if "vpa" in low:
            if "from vpa" in low and "credited" in low:
                m = re.search(r"from\s+VPA\s*([^@\s]+)@[^\s]+\s*\(UPI\s+\d+\)", message, re.I)
                if m:
                    u = m.group(1).strip()
                    if u: return self.clean_merchant_name(u)
            m = CompiledPatterns.HDFC.VPA_WITH_NAME.search(message)
            if m: return self.clean_merchant_name(m.group(1).strip())
            m = CompiledPatterns.HDFC.VPA_PATTERN.search(message)
            if m:
                u = m.group(1).strip()
                if len(u) > 3 and not u.isdigit(): return self.clean_merchant_name(u)

        if "spent on card" in low:
            m = CompiledPatterns.HDFC.SPENT_PATTERN.search(message)
            if m: return self.clean_merchant_name(m.group(1).strip())

        if "debited for" in low:
            m = CompiledPatterns.HDFC.DEBIT_FOR_PATTERN.search(message)
            if m: return self.clean_merchant_name(m.group(1).strip())

        if "upi mandate" in low:
            m = CompiledPatterns.HDFC.MANDATE_PATTERN.search(message)
            if m: return self.clean_merchant_name(m.group(1).strip())

        if "towards" in low:
            m = re.search(r"towards\s+([^\n]+?)(?:\s+UMRN|\s+ID:|\s+Alert:|$)", message, re.I)
            if m:
                merch = m.group(1).strip()
                if merch: return self.clean_merchant_name(merch)

        if "for:" in low:
            m = re.search(r"For:\s+([^\n]+?)(?:\s+From|\s+Via|$)", message, re.I)
            if m:
                merch = m.group(1).strip()
                if merch: return self.clean_merchant_name(merch)

        if "for " in low and "will be debited" in low:
            m = re.search(r"for\s+([^\n]+?)(?:\s+ID:|\s+Act:|$)", message, re.I)
            if m:
                merch = m.group(1).strip()
                if merch: return self.clean_merchant_name(merch)

        return super().extract_merchant(message, sender)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if self.is_investment_transaction(low): return TransactionType.INVESTMENT
        if "block cc" in low or "block pcc" in low: return TransactionType.CREDIT
        if "spent on card" in low and "block dc" not in low: return TransactionType.CREDIT
        if "payment" in low and "credit card" in low: return TransactionType.EXPENSE
        if "towards" in low and "credit card" in low: return TransactionType.EXPENSE
        if "sent" in low and "from hdfc" in low: return TransactionType.EXPENSE
        if "spent" in low and "from hdfc bank card" in low: return TransactionType.EXPENSE
        if "debited" in low: return TransactionType.EXPENSE
        if "withdrawn" in low and "block cc" not in low: return TransactionType.EXPENSE
        if "spent" in low and "card" not in low: return TransactionType.EXPENSE
        if any(kw in low for kw in ["charged", "paid", "purchase"]): return TransactionType.EXPENSE
        if any(kw in low for kw in ["credited", "deposited", "received", "refund"]): return TransactionType.INCOME
        if "cashback" in low and "earn cashback" not in low: return TransactionType.INCOME
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [CompiledPatterns.HDFC.REF_SIMPLE, CompiledPatterns.HDFC.UPI_REF_NO,
                CompiledPatterns.HDFC.REF_NO, CompiledPatterns.HDFC.REF_END]
        for p in pats:
            m = p.search(message)
            if m: return m.group(1).strip()
        return super().extract_reference(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r"Card\s+x(\d{4})", message, re.I)
        if m: return m.group(1)
        m = re.search(r"BLOCK\s+DC\s+(\d{4})", message, re.I)
        if m: return m.group(1)
        m = re.search(r"HDFC\s+Bank\s+([X\*]*\d+)", message, re.I)
        if m:
            d = "".join(filter(str.isdigit, m.group(1)))
            return d[-4:] if len(d) >= 4 else d
        pats = [CompiledPatterns.HDFC.ACCOUNT_DEPOSITED, CompiledPatterns.HDFC.ACCOUNT_FROM,
                CompiledPatterns.HDFC.ACCOUNT_SIMPLE, CompiledPatterns.HDFC.ACCOUNT_GENERIC]
        for p in pats:
            m = p.search(message)
            if m:
                s = m.group(1)
                return s[-4:] if len(s) >= 4 else s
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Avl\s+bal:?\s*INR\s*([0-9,]+(?:\.\d{2})?)",
                r"Available\s+Balance:?\s*INR\s*([0-9,]+(?:\.\d{2})?)",
                r"Bal\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        if self.is_e_mandate_notification(message): return False
        if self.is_future_debit_notification(message): return False
        low = message.lower()
        if "bill alert" in low or ("bill" in low and "is due on" in low): return False
        if "payment alert" in low and "will be" not in low: return True
        if any(kw in low for kw in ["has requested", "payment request", "to pay, download", "collect request", "ignore if already paid"]): return False
        if "received towards your credit card" in low: return False
        if "payment" in low and "credited to your card" in low: return False
        if any(kw in low for kw in ["otp", "one time password", "verification code", "offer", "discount", "cashback offer", "win "]): return False
        kw = ["debited", "credited", "withdrawn", "deposited", "spent", "received", "transferred", "paid", "sent", "deducted", "txn"]
        return any(k in low for k in kw)
