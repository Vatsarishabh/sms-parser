import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from transaction_type import TransactionType
from bank_parser import BankParser


class KotakBankParser(BankParser):
    """Kotak Bank specific parser."""

    BANK_CODE_MAP = {
        "okaxis": "Axis Bank", "okbizaxis": "Axis Bank Business",
        "okhdfcbank": "HDFC Bank", "okicici": "ICICI Bank", "oksbi": "State Bank of India",
        "paytm": "Paytm", "ybl": "PhonePe", "amazonpay": "Amazon Pay",
        "googlepay": "Google Pay", "airtel": "Airtel Money", "freecharge": "Freecharge",
        "mobikwik": "MobiKwik", "jupiteraxis": "Jupiter", "razorpay": "Razorpay",
        "bharatpe": "BharatPe",
    }

    PAYMENT_APP_PREFIXES = [
        "paytmqr","phonepeqr","phonepe.qr","gpay","amazonpayqr",
        "bhimqr","bharatpeqr","freechargeqr","mobikwikqr",
    ]

    def get_bank_name(self) -> str:
        return "Kotak Bank"

    def can_handle(self, sender: str) -> bool:
        upper = sender.upper()
        return bool(re.match(r'^[A-Z]{2}-KOTAKB-[ST]$', upper))

    def _clean_kotak_card_merchant(self, raw: str) -> str:
        m = re.match(r'^UPI-\d+-(.+)$', raw, re.IGNORECASE)
        if m:
            return self.clean_merchant_name(m.group(1).strip())
        return self.clean_merchant_name(raw)

    def _is_payment_app_id(self, name: str) -> bool:
        lower = name.lower()
        if any(lower.startswith(p) for p in self.PAYMENT_APP_PREFIXES):
            return True
        if len(name) > 20 and any(c.isalpha() for c in name) and any(c.isdigit() for c in name):
            return True
        return False

    def _merchant_from_bank_code(self, code: str) -> Optional[str]:
        return self.BANK_CODE_MAP.get(code.lower())

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        m = re.search(r'on\s+\d{1,2}-\w{3}-\d{2,4}\s+at\s+([^.]+?)(?:\.|Avl|$)', message, re.IGNORECASE)
        if m:
            merchant = self._clean_kotak_card_merchant(m.group(1).strip())
            if self.is_valid_merchant_name(merchant):
                return merchant

        to_pat = re.compile(r'to\s+([^\s]+@[^\s]+)\s+on', re.IGNORECASE)
        from_pat = re.compile(r'from\s+([^\s]+@[^\s]+)\s+on', re.IGNORECASE)
        match = to_pat.search(message) or from_pat.search(message)
        if match:
            upi_id = match.group(1).strip()
            if upi_id.startswith("upi") or upi_id[:3].lower() == "upi":
                name = upi_id[3:].split("@")[0]
                if name:
                    return self.clean_merchant_name(name) or None
            else:
                name = upi_id.split("@")[0]
                code = upi_id.split("@")[1] if "@" in upi_id else ""
                if self._is_payment_app_id(name):
                    result = self._merchant_from_bank_code(code) or self.clean_merchant_name(name)
                    return result
                elif name and name.isdigit():
                    return self._merchant_from_bank_code(code) or name
                elif name:
                    return self.clean_merchant_name(name)

        return super().extract_merchant(message, sender)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        lower = message.lower()
        if "avl limit" in lower or "avl lmt" in lower:
            return TransactionType.CREDIT
        if "credit card" in lower and ("spent" in lower or "debited" in lower):
            return TransactionType.CREDIT
        if "sent" in lower and "from kotak" in lower:
            return TransactionType.EXPENSE
        if "debited" in lower: return TransactionType.EXPENSE
        if "withdrawn" in lower: return TransactionType.EXPENSE
        if "spent" in lower: return TransactionType.EXPENSE
        if "charged" in lower: return TransactionType.EXPENSE
        if "paid" in lower: return TransactionType.EXPENSE
        if "purchase" in lower: return TransactionType.EXPENSE
        if "credited" in lower: return TransactionType.INCOME
        if "deposited" in lower: return TransactionType.INCOME
        if "received" in lower: return TransactionType.INCOME
        if "refund" in lower: return TransactionType.INCOME
        if "cashback" in lower and "earn cashback" not in lower: return TransactionType.INCOME
        return None

    def extract_reference(self, message: str) -> Optional[str]:
        m = re.search(r'UPI\s+Ref\s+([0-9]+)', message, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return super().extract_reference(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        m = re.search(r'Credit\s+Card\s+[xX*]*(\d{4})', message, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'AC\s+[X*]*([0-9]{4})(?:\s|,|\.)', message, re.IGNORECASE)
        if m:
            return m.group(1)
        return super().extract_account_last4(message)

    def extract_available_limit(self, message: str) -> Optional[Decimal]:
        for pat in [
            re.compile(r'Avl\s+limit:?\s*INR\s+([0-9,]+(?:\.\d{2})?)', re.IGNORECASE),
            re.compile(r'Avl\s+Lmt:?\s*INR\s+([0-9,]+(?:\.\d{2})?)', re.IGNORECASE),
            re.compile(r'Available\s+limit:?\s*INR\s+([0-9,]+(?:\.\d{2})?)', re.IGNORECASE),
        ]:
            m = pat.search(message)
            if m:
                try:
                    return Decimal(m.group(1).replace(",", ""))
                except InvalidOperation:
                    pass
        return super().extract_available_limit(message)

    def is_transaction_message(self, message: str) -> bool:
        lower = message.lower()
        if any(kw in lower for kw in [
            "otp","one time password","verification code","offer","discount","cashback offer","win "
        ]):
            return False
        if any(kw in lower for kw in [
            "has requested","payment request","collect request","requesting payment","requests rs","ignore if already paid"
        ]):
            return False
        keywords = ["sent","debited","credited","withdrawn","deposited","spent","received","transferred","paid"]
        return any(kw in lower for kw in keywords)
