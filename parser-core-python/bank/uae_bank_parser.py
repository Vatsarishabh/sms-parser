import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType
from parsed_transaction import ParsedTransaction

class UAEBankParser(BankParser):
    """
    Base abstract class for UAE bank parsers.
    Handles common patterns across UAE banks (AED currency, specific transaction types, etc.).
    """

    def contains_card_purchase(self, message: str) -> bool:
        return "Credit Card Purchase" in message or "Debit Card Purchase" in message or \
               "credit card purchase" in message.lower() or "debit card purchase" in message.lower()

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        transaction = super().parse(sms_body, sender, timestamp)
        if not transaction:
            return None
        
        extracted_currency = self.extract_currency(sms_body)
        if extracted_currency:
            transaction.currency = extracted_currency
        return transaction

    def extract_currency(self, message: str) -> Optional[str]:
        # Explicit patterns with [A-Z]{3}
        currency_patterns = [
            r"Amount\s+([A-Z]{3})",
            r"\b([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?",
            r"for\s+([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?",
            r"of\s+([A-Z]{3})\s+[0-9,]+(?:\.\d{2})?",
            r"[A-Z]{3}\s+([A-Z]{3})"
        ]

        for p in currency_patterns:
            matches = re.finditer(p, message, re.I)
            for match in matches:
                # Check all groups
                for group_val in match.groups():
                    if group_val:
                        upper_val = group_val.upper()
                        if len(upper_val) == 3 and upper_val.isalpha() and not self.is_month_abbreviation(upper_val):
                            return upper_val
        
        # Final fallback
        m = re.search(r"\b([A-Z]{3})\s+\d", message, re.I)
        if m:
            code = m.group(1).upper()
            if not self.is_month_abbreviation(code):
                return code

        return None

    def get_currency(self) -> str:
        return "AED"

    def extract_amount(self, message: str) -> Optional[Decimal]:
        # Generic multi-currency amount extraction for UAE banks
        iso_code_pattern = r"[A-Z]{3}"
        patterns = [
            r"(?:purchase of|transfer of|amount|for|of)\s+(" + iso_code_pattern + r")\s+([0-9,]+(?:\.\d{2})?)",
            r"(" + iso_code_pattern + r")\s+([0-9,]+(?:\.\d{2})?)",
            r"(" + iso_code_pattern + r")\s+\*+([0-9,]+(?:\.\d{2})?)" # Masked amount *123.45
        ]

        for p in patterns:
            m = re.search(p, message, re.I)
            if m:
                currency_code = m.group(1).upper()
                if self.is_month_abbreviation(currency_code):
                    continue

                amount_str = m.group(2).replace(",", "")
                
                if "*" in amount_str:
                    amount_str = amount_str.replace("*", "")
                    if not amount_str or amount_str == ".":
                        continue

                try:
                    return Decimal(amount_str)
                except (InvalidOperation, ValueError):
                    pass

        return super().extract_amount(message)

    def is_month_abbreviation(self, code: str) -> bool:
        months = {"JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"}
        return code in months

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()

        if "credit card purchase" in low: return TransactionType.CREDIT
        if self.contains_card_purchase(message): return TransactionType.EXPENSE

        if "cheque credited" in low: return TransactionType.INCOME
        if "cheque returned" in low: return TransactionType.EXPENSE

        if "atm cash withdrawal" in low or ("atm" in low and "withdrawn" in low):
            return TransactionType.EXPENSE

        if "inward remittance" in low or "cash deposit" in low or \
           "has been credited" in low or "is credited" in low:
            return TransactionType.INCOME

        if "outward remittance" in low or "payment instructions" in low:
            return TransactionType.EXPENSE
        if "funds transfer request" in low:
            return TransactionType.TRANSFER
        if "has been processed" in low:
            return TransactionType.EXPENSE

        if "credit" in low and "credit card" not in low and \
           "debit" not in low and "purchase" not in low and "payment" not in low:
            return TransactionType.INCOME

        if "debit" in low and "credit" not in low: return TransactionType.EXPENSE
        if "purchase" in low: return TransactionType.EXPENSE
        if "payment" in low: return TransactionType.EXPENSE

        return super().extract_transaction_type(message)
