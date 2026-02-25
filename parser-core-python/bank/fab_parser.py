import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

from uae_bank_parser import UAEBankParser
from transaction_type import TransactionType
from parsed_transaction import ParsedTransaction

class FABParser(UAEBankParser):
    """
    Parser for First Abu Dhabi Bank (FAB) - UAE's largest bank
    Handles AED currency transactions and global currencies for international transactions
    This class is designed to be inheritable by other UAE bank parsers like ADCB
    """

    def get_bank_name(self) -> str:
        return "First Abu Dhabi Bank"

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        if not self.is_transaction_message(sms_body):
            return None

        amount = self.extract_amount(sms_body)
        if amount is None:
            return None

        t_type = self.extract_transaction_type(sms_body)
        if t_type is None:
            return None

        currency = self.extract_currency(sms_body) or "AED"

        available_limit = None
        if t_type == TransactionType.CREDIT:
            available_limit = self.extract_available_limit(sms_body)

        from_acc, to_acc = (None, None)
        if t_type == TransactionType.TRANSFER:
            from_acc, to_acc = self.extract_transfer_accounts(sms_body)

        return ParsedTransaction(
            amount=amount,
            type=t_type,
            merchant=self.extract_merchant(sms_body, sender),
            reference=self.extract_reference(sms_body),
            account_last4=self.extract_account_last4(sms_body),
            balance=self.extract_balance(sms_body),
            credit_limit=available_limit,
            sms_body=sms_body,
            sender=sender,
            timestamp=timestamp,
            bank_name=self.get_bank_name(),
            is_from_card=self.contains_card_purchase(sms_body),
            currency=currency,
            from_account=from_acc,
            to_account=to_acc
        )

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        if any(k in up for k in ["FAB", "FABBANK", "ADFAB"]): return True
        return bool(re.match(r"^[A-Z]{2}-FAB-[A-Z]$", up))

    def extract_amount(self, message: str) -> Optional[Decimal]:
        iso_code = r"[A-Z]{3}"
        patterns = [
            r"funds transfer request of\s+(" + iso_code + r")\s+([0-9,]+(?:\.\d{2})?)",
            r"for\s+(" + iso_code + r")\s+([0-9,]+(?:\.\d{2})?)",
            r"(" + iso_code + r")\s+\*([0-9,]+(?:\.\d{2})?)",
            r"(" + iso_code + r")\s+([0-9*,]+(?:\.\d{2})?)",
            r"Amount\s*(" + iso_code + r")\s+\*([0-9,]+(?:\.\d{2})?)",
            r"Amount\s*(" + iso_code + r")\s+([0-9*,]+(?:\.\d{2})?)",
            r"payment.*?(" + iso_code + r")\s+\*([0-9,]+(?:\.\d{2})?)",
            r"payment.*?(" + iso_code + r")\s+([0-9*,]+(?:\.\d{2})?)"
        ]

        for p in patterns:
            m = re.search(p, message, re.I)
            if m:
                currency_code = m.group(1).upper()
                amount_str = m.group(2).replace(",", "")

                if "*" in amount_str:
                    if re.match(r"\*\d+(?:\.\d{2})?", amount_str):
                        amount_str = amount_str[1:]
                    elif re.match(r"\*+\.\d{2}", amount_str):
                        amount_str = "0" + amount_str[amount_str.find('.'):]
                    else:
                        num_m = re.search(r"(\d+(?:\.\d{2})?)", amount_str)
                        if num_m:
                            amount_str = num_m.group(1)
                        else:
                            return super().extract_amount(message)

                try:
                    return Decimal(amount_str)
                except (InvalidOperation, ValueError):
                    pass

        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        if self.contains_card_purchase(message):
            m1 = re.search(r"(?:Credit|Debit)\s+Card\s+Purchase\s+Card\s+No\s+[X\d]+\s+[A-Z]{3}\s+[\d,.]+\s+([^0-9]+?)(?:\s+\d{2}/\d{2}/\d{2})", message, re.I)
            if m1:
                mer = m1.group(1).strip().replace("*", "").strip()
                if mer: return self.clean_merchant_name(mer)

            lines = message.split("\n")
            cur_idx = -1
            for i, line in enumerate(lines):
                if re.search(r"[A-Z]{3}\s+[0-9,]+(?:\.\d{2})?", line, re.I):
                    cur_idx = i
                    break
            
            if cur_idx != -1 and cur_idx + 1 < len(lines):
                mer_line = lines[cur_idx + 1].strip().replace("*", "").strip()
                if mer_line and "/" not in mer_line:
                    return self.clean_merchant_name(mer_line)

            m_card = re.search(r"Card\s+[X\*]+(\d{4})", message, re.I)
            if m_card:
                c_idx = -1
                for i, line in enumerate(lines):
                    if m_card.group(0) in line:
                        c_idx = i
                        break
                if c_idx != -1 and c_idx + 2 < len(lines):
                    mer_line = lines[c_idx + 2].strip()
                    if mer_line and "Available Balance" not in mer_line and not re.match(r"\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}", mer_line):
                        mer_line = mer_line.replace("*", "").strip()
                        return self.clean_merchant_name(mer_line)

            m_site = re.search(r"([A-Z]+\.(?:COM|NET|ORG|IN)[^\n]*)", message, re.I)
            if m_site:
                mer = m_site.group(1).strip().replace("*", "").strip()
                return self.clean_merchant_name(mer)

        if "payment instructions" in message.lower() or "funds transfer request" in message.lower():
            if "funds transfer request" in message.lower():
                return self.format_transfer_merchant(self.extract_transfer_accounts(message))

            m_to = re.search(r"to\s+([^\s]+)", message, re.I)
            if m_to:
                recip = m_to.group(1)
                if "*" in recip:
                    vis = "".join(filter(str.isdigit, recip))
                    if vis: return f"Transfer to {vis[-4:] if len(vis)>=4 else vis}"
                digs = "".join(filter(lambda c: c.isdigit() or c == 'X', recip))
                if digs: return f"Transfer to {digs[-4:]}"

        if "has been credited to your fab account" in message.lower() and "unsuccessful transaction" not in message.lower():
            return "Account Credited"

        tx_merchants = {
            "ATM Cash withdrawal": "ATM Withdrawal",
            "Inward Remittance": "Inward Remittance",
            "Outward Remittance": "Outward Remittance",
            "Cash Deposit": "Cash Deposit",
            "Cheque Credited": "Cheque Credited",
            "Cheque Returned": "Cheque Returned",
            "Cash withdrawal": "Cash Withdrawal",
            "unsuccessful transaction": "Refund"
        }
        for k, v in tx_merchants.items():
            if k.lower() in message.lower(): return v

        return super().extract_merchant(message, sender)

    def extract_account_last4(self, message: str) -> Optional[str]:
        if "funds transfer request" in message.lower():
            from_acc, _ = self.extract_transfer_accounts(message)
            if from_acc: return from_acc
        return self.extract_standard_account_last4(message)

    def extract_balance(self, message: str) -> Optional[Decimal]:
        iso_code = r"[A-Z]{3}"
        p = r"(?:Available|available)\s+[Bb]alance\s+(?:is\s+)?(" + iso_code + r")\s*\*{0,}([0-9*,]+(?:\.\d{2})?)"
        m = re.search(p, message, re.I)
        if m:
            bal_str = m.group(2).replace(",", "")
            if "*" in bal_str:
                if re.match(r"\*+\d+(?:\.\d{2})?", bal_str):
                    bal_str = bal_str.replace("*", "")
                elif re.match(r"\*+\.\d{2}", bal_str):
                    bal_str = "0" + bal_str[bal_str.find('.'):]
                else:
                    return None
            try:
                return Decimal(bal_str)
            except (InvalidOperation, ValueError):
                pass
        return super().extract_balance(message)

    def extract_reference(self, message: str) -> Optional[str]:
        m1 = re.search(r"(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2})", message)
        if m1: return m1.group(1)
        m2 = re.search(r"Value\s+Date\s+(\d{2}/\d{2}/\d{4})", message, re.I)
        if m2: return m2.group(1)
        return super().extract_reference(message)

    def format_transfer_merchant(self, accounts: Tuple[Optional[str], Optional[str]]) -> str:
        f_acc, t_acc = accounts
        if f_acc and t_acc: return f"Transfer: {f_acc[-3:]} → {t_acc[-3:]}"
        if f_acc: return f"Transfer from {f_acc[-3:]}"
        if t_acc: return f"Transfer to {t_acc[-3:]}"
        return "Transfer"

    def extract_standard_account_last4(self, message: str) -> Optional[str]:
        pats = [r"Card\s+No\s+([X\d]{4})", r"Account\s+([X\d]{4})\*{0,2}", r"Account\s+[X\*]+(\d{4})"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                acc = m.group(1).replace("X", "")
                if acc: return acc
        return super().extract_account_last4(message)

    def extract_transfer_accounts(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        f_pats = [r"from\s+account\s+([X\d]{4,})", r"from\s+account/card\s+([X\d]{4,})", r"from your account/card\s+([X\d]{4,})", r"from\s+([X\d]{4,})\s+to\s+account"]
        t_pats = [r"to\s+account\s+([X\d]{4,})", r"to\s+IBAN/Account/Card\s+([X\d]{4,})", r"to\s+IBAN/Account/Card\s+([X\d]{4,})\s+has been processed successfully from", r"to\s+([X\d]{4,})\s+from\s+account"]

        def extract(pats):
            for p in pats:
                m = re.search(p, message, re.I)
                if m: return m.group(1).replace("X", "")[-4:]
            return None

        return extract(f_pats), extract(t_pats)

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        non_txn = ["declined due to insufficient balance", "transaction has been declined", "address update request", "statement request", "stamped statement", "cannot process your", "amazing rate", "request has been logged", "reference number", "beneficiary creation/modification request", "funds transfer request is under process", "has been resolved", "funds transfer request has failed", "card has been successfully activated", "temporarily blocked", "never share credit/debit card", r"debit card.*replacement request", r"card will be ready for dispatch", r"replacement request has been registered", "otp", "activation", "thank you for activating", "do not disclose your otp", "atyourservice@bankfab.com", "has been blocked on"]
        if any(re.search(k, low) for k in non_txn): return False

        if any(k in low for k in ["bit.ly", "conditions apply", "instalments at 0% interest"]):
            if not any(k in low for k in ["purchase", "payment instructions", "remittance"]): return False

        tx_kw = ["credit card purchase", "debit card purchase", "inward remittance", "outward remittance", "atm cash withdrawal", "payment instructions", "has been processed", "has been credited to your fab account", "cash deposit", "cheque credited", "cheque returned"]
        if "funds transfer request of" in low and "has been processed" in low: return True
        if any(k in low for k in tx_kw): return True

        if any(k in low for k in ["credit", "debit", "remittance", "available balance"]):
            if "credit card" in low and "credit" in low: pass # still check amount
            iso_code = r"[A-Z]{3}"
            if re.search(iso_code + r"\s+[0-9,]+(?:\.\d{2})?", low): return True

        return super().is_transaction_message(message)
