import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from fab_parser import FABParser
from transaction_type import TransactionType

class ADCBParser(FABParser):
    """
    Parser for Abu Dhabi Commercial Bank (ADCB) - UAE's largest bank by assets
    Inherits from FABParser since ADCB follows similar UAE banking patterns
    Handles AED currency and multi-currency international transactions
    """

    def get_bank_name(self) -> str:
        return "Abu Dhabi Commercial Bank"

    def get_currency(self) -> str:
        return "AED"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "ADCBALERT" or "ADCB" in up or "ADCBANK" in up or bool(re.match(r"^[A-Z]{2}-ADCB-[A-Z]$", up))

    def extract_amount(self, message: str) -> Optional[Decimal]:
        iso_code = r"[A-Z]{3}"
        patterns = [
            r"was used for\s+(" + iso_code + r")\s*([0-9,]+(?:\.\d{2})?)",
            r"used for\s+(" + iso_code + r")\s*([0-9,]+(?:\.\d{2})?)",
            r"\b(" + iso_code + r")\s*([0-9,]+(?:\.\d{2})?)\s+withdrawn from",
            r"\b(" + iso_code + r")\s*([0-9,]+(?:\.\d{2})?)\s+has been deposited via ATM",
            r"\b(" + iso_code + r")\s*([0-9,]+(?:\.\d{2})?)\s+transferred via",
            r"Cr\. transaction of\s+(" + iso_code + r")\s*([0-9,]+(?:\.\d{2})?)",
            r"Dr\.?\s*transaction of\s+(" + iso_code + r")\s*([0-9,]+(?:\.\d{2})?)",
            r"Transaction of\s+(" + iso_code + r")\s*([0-9,]+(?:\.\d{2})?)",
            r"Amount Paid:\s*(" + iso_code + r")\s*([0-9,]+(?:\.\d{2})?)"
        ]

        for p in patterns:
            m = re.search(p, message, re.I)
            if m:
                cur = m.group(1).upper()
                amt_str = m.group(2).replace(",", "")
                if len(cur) == 3 and cur.isalpha() and not self.is_month_abbreviation(cur):
                    try:
                        amt = Decimal(amt_str)
                        if amt > Decimal("0.01"):
                            return amt.quantize(Decimal("0.01")) if amt.as_tuple().exponent > -2 else amt
                    except (InvalidOperation, ValueError):
                        pass

        if self.contains_card_purchase(message):
            after = message.split("was used for")[-1]
            m = re.search(r"([A-Z]{3})\s*([0-9,]+(?:\.\d{2})?)", after)
            if m:
                cur = m.group(1).upper()
                amt_str = m.group(2).replace(",", "")
                if len(cur) == 3 and cur.isalpha() and not self.is_month_abbreviation(cur):
                    try:
                        amt = Decimal(amt_str)
                        if amt > Decimal("0.01"):
                            return amt.quantize(Decimal("0.01")) if amt.as_tuple().exponent > -2 else amt
                    except (InvalidOperation, ValueError):
                        pass

        return None

    def contains_card_purchase(self, message: str) -> bool:
        return "was used for" in message.lower() or "used for" in message.lower()

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        if self.contains_card_purchase(message):
            m = re.search(r"at\s+([^,\n]+),\s*[A-Z]{2}", message, re.I)
            if m: return self.clean_merchant_name(m.group(1).strip())

        if "TouchPoints Redemption" in message or "touchpoints redemption" in message.lower():
            return "TouchPoints Redemption"

        if "withdrawn from" in message.lower():
            after_at = message.split("at ")[-1]
            before_bal = after_at.split(" Avl.Bal")[0].split("Available balance")[0]
            atm_info = re.sub(r"\s+", " ", before_bal).strip()
            if atm_info and (atm_info.startswith("ATM-") or atm_info.startswith("ATM ")):
                nm = atm_info[4:].strip()
                nm = re.sub(r"^\d+", "", nm).replace(".", "").strip()
                if nm: return f"ATM Withdrawal: {nm}"

        if "deposited via ATM" in message.lower():
            after = message.split("deposited via ATM")[-1]
            m = re.search(r"at\s+([^.\n]+)", after, re.I)
            if m: return f"ATM Deposit: {m.group(1).strip()}"

        if "transferred via" in message.lower(): return "Transfer via ADCB Banking"
        if "Cr. transaction" in message.lower(): return "Account Credit"
        if "Dr. transaction" in message.lower(): return "Account Debit"

        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        pats = [
            r"debit card\s+[X\*]+(\d{4})\s+linked to acc\.?\s*[X\*]+(\d{6})",
            r"linked to acc\.?\s*[X\*]+(\d{6})",
            r"withdrawn from acc\.?\s*[X\*]+(\d{6})",
            r"in your account\s+[X\*]+(\d{6})",
            r"from acc\.?\s*no\.?\s*[X\*]+(\d{6})",
            r"account (?:number\s*)?[X\*]+(\d{6})",
            r"on your account number\s+[X\*]+(\d{6})",
            r"debit card\s+[X\*]+(\d{4})\s+linked to acc\.?\s*[X\*]+(\d{4})",
            r"withdrawn from acc\.?\s*[X\*]+(\d{4})",
            r"in your account\s+[X\*]+(\d{4})",
            r"from acc\.?\s*no\.?\s*[X\*]+(\d{4})",
            r"account (?:number\s*)?[X\*]+(\d{4})",
            r"Card\s+[X\*]+(\d{4})"
        ]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                if len(m.groups()) > 1 and m.group(2): return m.group(2)
                if m.group(1): return m.group(1)
        return super().extract_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        pats = [
            r"Avl\.Bal\s+([A-Z]{3})\s+([0-9,]+(?:\.\d{2})?)",
            r"Available balance is\s+([A-Z]{3})?\s*([0-9,]+(?:\.\d{2})?)",
            r"Avl\.?\s*bal\.?\s+([A-Z]{3})\s+([0-9,]+(?:\.\d{2})?)",
            r"Avl\.Bal\.?([A-Z]{3})([0-9,]+(?:\.\d{2})?)",
            r"Available Balance is\s+([A-Z]{3})([0-9,]+(?:\.\d{2})?)"
        ]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                bal_str = m.group(2) if len(m.groups()) > 1 and m.group(2) else m.group(1)
                try: return Decimal(bal_str.replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        pats = [r"on\s+(\w{3}\s+\d{1,2}\s+\d{4}\s+\d{1,2}:\d{2}[AP]M)", r"(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2})"]
        for p in pats:
            m = re.search(p, message)
            if m: return m.group(1)
        return super().extract_reference(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if self.contains_card_purchase(message): return TransactionType.EXPENSE
        if "withdrawn from" in low and "atm" in low: return TransactionType.EXPENSE
        if "deposited via atm" in low: return TransactionType.INCOME
        if "transferred via" in low: return TransactionType.TRANSFER
        if "cr. transaction" in low: return TransactionType.INCOME
        if "dr. transaction" in low: return TransactionType.EXPENSE
        if "touchpoints redemption" in low: return TransactionType.EXPENSE
        return super().extract_transaction_type(message)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        non_tx = ["could not be completed", "insufficient funds", r"transaction.*could not be completed", "do not share your otp", "otp for transaction", "activation key", "do not share with anyone", "has been de-activated", "has been activated", "congratulations on the first usage", "digital card assigned to", "pin change/setup was successful", "request for pin change/setup", "we have updated your emirates id", "confirmation recd. from", "sr no.", "for clarifications please call", "for assistance please call"]
        if any(re.search(k, low, re.I) for k in non_tx): return False

        tx_kw = ["your debit card", "your credit card", "was used for", "used for", "withdrawn from", "deposited via atm", "transferred via", "cr. transaction", "dr. transaction", "cr.transaction", "dr.transaction", r"transaction.*was successful", "touchpoints redemption", r"debit card.*used for", "touchpoints redemption request", r"account number XXX.*was successful"]
        if any(re.search(k, low) for k in tx_kw): return True
        return super().is_transaction_message(message)

    def extract_currency(self, message: str) -> Optional[str]:
        pats = [r"was used for\s+([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?", r"used for\s+([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?", r"\b([A-Z]{3})\s*[0-9,]+(?:\.\d{2})?\s+withdrawn from", r"\b([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?\s+has been deposited via ATM", r"\b([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?\s+transferred via", r"Cr\.?\s*transaction of\s+([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?", r"Dr\.?\s*transaction of\s+([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?", r"Transaction of\s+([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?", r"Amount Paid:\s*([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                cur = m.group(1).upper()
                if len(cur) == 3 and cur.isalpha() and not self.is_month_abbreviation(cur): return cur

        if self.contains_card_purchase(message):
            after = message.split("was used for" if "was used for" in message.lower() else "used for")[-1]
            before_bal = after.split(" Avl.Bal")[0].split(" Available balance")[0]
            m = re.search(r"([A-Z]{3})\s*[0-9,]+(?:\.\d{2})?", before_bal)
            if m:
                cur = m.group(1).upper()
                if len(cur) == 3 and cur.isalpha() and not self.is_month_abbreviation(cur): return cur

        return "AED"
