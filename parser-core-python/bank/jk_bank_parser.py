import re
import hashlib
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class JKBankParser(BaseIndianBankParser):
    """
    Jammu & Kashmir Bank (JK Bank) specific parser.
    """

    def get_bank_name(self) -> str:
        return "JK Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if up in {"JKBANK", "JKB", "JKBANKL", "JKBNK"}: return True
        pats = [r"^[A-Z]{2}-JKBANK.*$", r"^[A-Z]{2}-JKB.*$", r"^[A-Z]{2}-JKBNK.*$", r"^JKBANK-[A-Z]+$", r"^JKB-[A-Z]+$"]
        return any(re.match(p, up) for p in pats)

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        pt = super().parse(sms_body, sender, timestamp)
        if not pt: return None
        
        pt.transactionHash = self._generate_jk_bank_hash(pt, sms_body, sender)
        return pt

    def _generate_jk_bank_hash(self, transaction: ParsedTransaction, sms_body: str, sender: str) -> str:
        norm_amt = transaction.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ref = transaction.reference
        time_str = self._extract_txn_time(sms_body)

        if ref and time_str:
            data = f"JKBANK|{norm_amt}|REF:{ref}|TIME:{time_str}"
        elif ref:
            data = f"JKBANK|{norm_amt}|REF:{ref}"
        elif time_str and transaction.balance:
            norm_bal = transaction.balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            data = f"JKBANK|{norm_amt}|TIME:{time_str}|BAL:{norm_bal}"
        elif time_str:
            data = f"JKBANK|{norm_amt}|TIME:{time_str}"
        elif transaction.balance:
            norm_bal = transaction.balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            data = f"JKBANK|{norm_amt}|{sender}|BAL:{norm_bal}"
        else:
            data = f"{sender}|{norm_amt}|{transaction.timestamp}"

        return hashlib.md5(data.encode()).hexdigest()

    def _extract_txn_time(self, message: str) -> Optional[str]:
        m1 = re.search(r"at\s+(\d{1,2}:\d{2}(?::\d{2})?)", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"on\s+(\d{1,2}-\w{3}-\d{2,4})\s+at\s+(\d{1,2}:\d{2})", message, re.I)
        if m2: return f"{m2.group(1)} {m2.group(2)}"
        m3 = re.search(r"on\s+(\d{1,2}-\w{3}-\d{2,4})", message, re.I)
        if m3: return m3.group(1)
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "imps fund transfer" in low:
            m = re.search(r"Amt\s+received\s+from\s+([^h]+?)(?:\s+having\s+A/C|$)", message, re.I)
            if m and m.group(1).strip(): return self.clean_merchant_name(m.group(1).strip())
            m = re.search(r"received\s+from\s+([^.\n]+?)(?:\s+having|\s+with|$)", message, re.I)
            if m and m.group(1).strip(): return self.clean_merchant_name(m.group(1).strip())
            return "IMPS Transfer"
            
        if any(k in low for k in ["tin/tax information", "tin/tax informat"]): return "Tax Information Network"
        if "atm recovery" in low: return "ATM Recovery Charge"
        
        m_tow = re.search(r"towards\s+([^.\n]+?)(?:\.\s*Avl|\.\s*Available|\.\s*To\s+dispute|$)", message, re.I)
        if m_tow:
            mer = m_tow.group(1).strip()
            if any(k in mer.lower() for k in ["tin/tax informat", "tin/tax information"]): return "Tax Information Network"
            return self.clean_merchant_name(mer)
            
        m_txn = re.search(r"(?:Debited|Credited)\s+by\s+INR\s+[\d,]+(?:\.\d{2})?\s+at\s+[\d:]+\s+by\s+([^.\n]+?)(?:\.|Available|$)", message, re.I)
        if m_txn:
            mer = m_txn.group(1).strip()
            if any(k in mer.upper() for k in ["CHRGS", "CHARGES"]): return None
            if "INDIAN CLEARING CORPO" in mer.upper(): return "Indian Clearing Corporation"
            if "CLEARING CORPO" in mer.upper(): return "Clearing Corporation"
            if "NSE CLEARING" in mer.upper(): return "NSE Clearing"
            if "BSE CLEARING" in mer.upper(): return "BSE Clearing"
            if "RTGS" in mer.upper() and "CLEARING" not in mer.upper(): return "RTGS Transfer"
            if "NEFT" in mer.upper(): return "NEFT Transfer"
            if "IMPS" in mer.upper(): return "IMPS Transfer"
            if "ETFR" in mer.upper(): return "Transfer"
            if "MTFR" in mer.upper():
                mm = re.search(r"mTFR/\d+/(.+)", mer, re.I)
                return self.clean_merchant_name(mm.group(1).strip()) if mm else "Mobile Transfer"
            if "TIN" in mer.upper(): return "Tax Information Network"
            return self.clean_merchant_name(mer.split("/")[0])
            
        m_sim = re.search(r"by\s+([^.\n]+?)(?:\.|Available|$)", message, re.I)
        if m_sim:
            mer = m_sim.group(1).strip()
            if not mer.upper().startswith("INR"): return self.clean_merchant_name(mer)
            
        if "via upi from" in low:
            m = re.search(r"via\s+UPI\s+from\s+([^.\n]+?)\s+on", message, re.I)
            if m and self.is_valid_merchant_name(m.group(1).strip()): return self.clean_merchant_name(m.group(1).strip())
            
        m_mtfr = re.search(r"mTFR/\d+/([^.\n]+?)(?:\.|A/C|$)", message, re.I)
        if m_mtfr and self.is_valid_merchant_name(m_mtfr.group(1).strip()): return self.clean_merchant_name(m_mtfr.group(1).strip())
        
        if "via upi" in low:
            m = re.search(r"to\s+([^@\s]+@[^\s]+)", message, re.I)
            if m:
                nm = m.group(1).strip().split("@")[0]
                if nm and nm.lower() != "upi": return self.clean_merchant_name(nm)
            m = re.search(r"to\s+([^.\n]+?)\s+via\s+UPI", message, re.I)
            if m and self.is_valid_merchant_name(m.group(1).strip()): return self.clean_merchant_name(m.group(1).strip())
            return "UPI"
            
        if "atm" in low or "withdrawn" in low: return "ATM"
        
        for p in [r"to\s+([^.\n]+?)\s+via", r"from\s+([^.\n]+?)(?:\s+on|\s+Ref|$)", r"at\s+([^.\n]+?)(?:\s+on|\s+Ref|$)", r"for\s+([^.\n]+?)(?:\s+on|\s+Ref|$)"]:
            m = re.search(p, message, re.I)
            if m:
                mer = self.clean_merchant_name(m.group(1).strip())
                if self.is_valid_merchant_name(mer): return mer
                
        return super().extract_merchant(message, sender)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(k in low for k in ["clearing corpo", "indian clearing", "nse clearing", "bse clearing", "iccl", "nsccl"]):
            if "credited" in low: return TransactionType.INVESTMENT
            if "debited" in low: return TransactionType.INVESTMENT
            return None
        if "has been debited" in low or "debited" in low or "withdrawn" in low or "spent" in low or "charged" in low or "paid" in low or "purchase" in low or "transferred" in low: return TransactionType.EXPENSE
        if "has been credited" in low or "credited" in low or "deposited" in low or "received" in low or "refund" in low: return TransactionType.INCOME
        if "cashback" in low and "earn cashback" not in low: return TransactionType.INCOME
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"RRN\s+No\.?\s*(\d+)", r"UPI\s+Ref[:\s]+(\d+)", r"txn\s+Ref[:\s]+([A-Z0-9]+)", r"Reference[:\s]+([A-Z0-9]+)", r"Ref\s+No[:\s]+([A-Z0-9]+)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1).strip()
        return super().extract_reference(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [r"Your\s+A\/c\s+[X]+(\d{4})", r"JK\s+Bank\s+A\/c\s+no\.\s+[X]+(\d{4})", r"A\/c\s+X{3}(\d{4})", r"A\/c\s+[X]*(\d{4})", r"Account\s+[X]+(\d{4})", r"A\/c\s+ending\s+(\d{4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Available\s+Bal\s+is\s+INR\s*([0-9,]+(?:\.\d{2})?)\s*(?:Cr|Dr)?",
                r"A/C\s+Bal\s+is\s+INR\s*([0-9,]+(?:\.\d{2})?)\s*(?:Cr|Dr)?",
                r"Avl\s+Bal[:\s]+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Balance[:\s]+Rs\.?\s*([0-9,]+(?:\.\d{2})?)",
                r"Bal\s+Rs\.?\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "one time password", "verification code", "offer", "discount", "cashback offer", "win ", "has requested", "payment request", "collect request", "requesting payment"]): return False
        if any(k in low for k in ["your rtgs txn", "your neft txn", "your imps txn"]) and "has been credited" in low: return False
        kw = ["has been debited", "has been credited", "debited", "credited", "withdrawn", "deposited", "spent", "received", "transferred", "paid"]
        return any(k in low for k in kw)
