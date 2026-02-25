import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class StandardCharteredBankParser(BankParser):
    """
    Parser for Standard Chartered Bank SMS messages (India and Pakistan).
    """

    def get_bank_name(self) -> str:
        return "Standard Chartered Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if any(k in up for k in ["SCBANK", "STANCHART", "STANDARDCHARTERED", "STANDARD CHARTERED"]) or up == "9220":
            return True
        return bool(re.match(r"^[A-Z]{2}-SCBANK-[A-Z]$", up))

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        parsed = super().parse(sms_body, sender, timestamp)
        if not parsed: return None
        
        cur = parsed.currency
        low = sms_body.lower()
        if "pkr" in low: cur = "PKR"
        elif "usd" in low: cur = "USD"
        
        parsed.currency = cur
        return parsed

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"PKR\s+([0-9,]+(?:\.\d{2})?)",
                r"\b(?:USD)\s+([0-9,]+(?:\.\d{2})?)",
                r"is debited for Rs\.\s*([0-9,]+(?:\.\d{2})?)",
                r"(?:NEFT|RTGS|IMPS)\s+credit\s+of\s+INR\s+([0-9,]+(?:\.\d{2})?)",
                r"is credited for Rs\.\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        # Pakistan
        if "payment of" in low and "financing" in low: return TransactionType.EXPENSE
        if "transaction of pkr" in low and "using online banking" in low: return TransactionType.EXPENSE
        if "withdrawn from account" in low or "cash withdrawal transaction" in low or "paid at" in low: return TransactionType.EXPENSE
        if "transaction of pkr" in low and "to" in low: return TransactionType.TRANSFER
        if "sent to scb pk" in low or ("electronic funds transfer" in low and "into your account" in low) or "has been credited" in low:
            return TransactionType.INCOME
        # India
        if "is debited for" in low: return TransactionType.EXPENSE
        if any(k in low for k in ["neft credit", "rtgs credit", "imps credit", "is credited for"]): return TransactionType.INCOME
        return super().extract_transaction_type(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "sent to scb pk" in low: return "RAAST Transfer"
        if "financing facility" in low: return "Financing Payment"
        if "withdrawn" in low or "cash withdrawal" in low: return "ATM Cash Withdrawal"
        
        m1 = re.search(r"and credited to a/c ([X\*]+\d+)", message, re.I)
        if m1: return f"UPI Transfer to {m1.group(1)}"
        
        if "neft credit" in low: return "NEFT Credit"
        if "rtgs credit" in low: return "RTGS Credit"
        if "imps credit" in low: return "IMPS Credit"
        
        m2 = re.search(r"paid at\s+([A-Za-z0-9\s.\-]+?)\s+on", message, re.I)
        if m2: return self.clean_merchant_name(m2.group(1))
        
        m3 = re.search(r"to\s+([A-Za-z0-9*]+)(?:\s|$)", message, re.I)
        if m3:
            dst = m3.group(1)
            if dst.lower() not in ["your", "account", "iban", "acct"]:
                if all(c == '*' for c in dst): return "Transfer"
                if dst.startswith("****"): return f"Transfer to {dst[-4:]}"
                if 3 <= len(dst) <= 8: return self.clean_merchant_name(dst) if any(c.isalpha() for c in dst) else f"Transfer to {dst}"
                return "Transfer"
                
        m4 = re.search(r"from account\s+[A-Za-z0-9\-*xX]+(?:\s+([A-Z][A-Za-z0-9\s]+?))(?:\s+from\s+IBFT|\s+via|\s+on|\s*$)", message, re.I)
        if m4:
            nm = m4.group(1).strip()
            if nm: return self.clean_merchant_name(nm)
            
        if re.search(r"from account\s+[A-Za-z0-9\-*xX]+", message, re.I): return "IBFT Transfer"
        if "raast" in low: return "RAAST Transfer"
        if "ibft" in low or "electronic funds transfer" in low: return "IBFT Transfer"
        
        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m1 = re.search(r"Your a/c ([X*]+)(\d{4})", message, re.I)
        if m1: return m1.group(2)
        m2 = re.search(r"in your account (?:\d+[xX*]+)?(\d{4})", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"(?:A/C\s*[*Xx]+|Account No\.\s*[0-9Xx*]+|Acc\. Number\s*[0-9Xx*]+|Iban\.\s*[*Xx]+)(\d{4})", message, re.I)
        if m3: return m3.group(1)
        m4 = re.search(r"card no\.?\s*[0-9Xx*\s-]*?(\d{4})(?![0-9Xx])", message, re.I)
        if m4: return m4.group(1)
        m5 = re.search(r"your account\s+[0-9\-*xX]+", message, re.I)
        if m5:
            dig = "".join(filter(str.isdigit, m5.group(0)))
            if len(dig) >= 4: return dig[-4:]
        m6 = re.search(r"account\s+[0-9\-*xX]+", message, re.I)
        if m6:
            dig = "".join(filter(str.isdigit, m6.group(0)))
            if len(dig) >= 4: return dig[-4:]
            if len(dig) >= 2: return dig[-2:]
        return super().extract_account_last4(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"UPI Ref no (\d+)", message, re.I)
        if m1: return m1.group(1)
        m2 = re.search(r"TX ID ([A-Z0-9]+)", message, re.I)
        if m2: return m2.group(1)
        m3 = re.search(r"Transaction ID:([A-Z0-9\-]+)", message, re.I)
        if m3: return m3.group(1)
        return super().extract_reference(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [r"Available Balance:\s*INR\s+([0-9,]+(?:\.\d{2})?)",
                r"Avail Limit\s*PKR\s*([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        keys = ["is debited for", "is credited for", "neft credit", "rtgs credit", "imps credit", "withdrawn from account", "cash withdrawal transaction", "paid at", "payment of", "transaction of pkr", "sent to scb pk", "electronic funds transfer", "has been credited"]
        if any(k in low for k in keys): return True
        return super().is_transaction_message(message)
