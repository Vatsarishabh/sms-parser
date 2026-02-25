import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from base_indian_bank_parser import BaseIndianBankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class FederalBankParser(BaseIndianBankParser):
    """
    Parser for Federal Bank SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Federal Bank"

    def can_handle(self, sender: str) -> bool:
        norm = sender.upper()
        return any(k in norm for k in ["FEDBNK", "FEDERAL", "FEDFIB", "FEDSCP"]) or \
               re.match(r"^[A-Z]{2}-FEDBNK-S$", norm) or \
               re.match(r"^[A-Z]{2}-FEDSCP-S$", norm) or \
               re.match(r"^[A-Z]{2}-FedFiB-[A-Z]$", norm) or \
               re.match(r"^[A-Z]{2}-FEDBNK-[TPG]$", norm) or \
               re.match(r"^[A-Z]{2}-FEDBNK$", norm)

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        if "Your available balance for a/c" in sms_body:
            return self._parse_balance_inquiry(sms_body, sender, timestamp)
        return super().parse(sms_body, sender, timestamp)

    def _parse_balance_inquiry(self, message: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        m = re.search(r"([A-Z]{2,3}\d{4})\s+is\s+INR\s+([0-9,]+(?:\.\d{1,2})?)(?=[,.]|\s+\.)", message, re.I)
        if not m: return None
        
        acc_no = m.group(1)
        bal_str = m.group(2).replace(",", "")
        
        # Area check for masks
        area_m = re.search(r"([A-Z]{2,3}\d{4})\s+is\s+INR\s+[0-9,x.]+", message, re.I)
        if area_m and "x" in area_m.group(0).lower(): return None

        try:
            balance = Decimal(bal_str)
            return ParsedTransaction(
                amount=Decimal("0.0"),
                type=TransactionType.BALANCE_UPDATE,
                merchant="Balance Inquiry",
                reference=None,
                accountLast4=acc_no[-4:],
                balance=balance,
                smsBody=message,
                sender=sender,
                timestamp=timestamp,
                bankName=self.get_bank_name(),
                isFromCard=False,
                currency="INR"
            )
        except (InvalidOperation, ValueError): return None

    def detect_is_card(self, message: str) -> bool:
        low = message.lower()
        if "credit card" in low: return True
        if "debit card" in low: return True
        if "card xx**" in low or "card ending with" in low: return True
        if re.search(r"inr\s+[\d,]+(?:\.\d{2})?\s+spent", low): return True
        if " spent " in low and " at " in low and " on " in low: return True
        if ("e-mandate" in low or "payment of" in low) and \
           ("federal bank debit card" in low or "federal bank credit card" in low): return True
           
        if "via upi" in low or "to vpa" in low: return False
        if "atm" in low: return False
        if "withdrawn" in low and "card" not in low: return False
        if any(k in low for k in ["via imps", "via neft", "via rtgs"]): return False
        return False

    def extract_amount(self, message: str) -> Optional[Decimal]:
        pats = [r"₹\s*([0-9,]+(?:\.\d{2})?)",
                r"INR\s+([0-9,]+(?:\.\d{2})?)\s+spent",
                r"you've received INR\s+([0-9,]+(?:\.\d{2})?)",
                r"Rs\s+([0-9,]+(?:\.\d{2})?)\s+debited",
                r"Rs\s+([0-9,]+(?:\.\d{2})?)\s+sent",
                r"Rs\s+([0-9,]+(?:\.\d{2})?)\s+credited",
                r"has\s+received\s+Rs\s+([0-9,]+(?:\.\d{2})?)\s+from",
                r"withdrawn\s+Rs\s+([0-9,]+(?:\.\d{2})?)"]
        for p in pats:
            m = re.search(p, message, re.I)
            if m:
                try: return Decimal(m.group(1).replace(",", ""))
                except (InvalidOperation, ValueError): pass
        return super().extract_amount(message)

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        if "withdrawn" in message.lower(): return "Cash Withdrawal"
        
        m1 = re.search(r"^([A-Z][A-Za-z0-9\s]+?)\s+has\s+received\s+Rs", message, re.I)
        if m1:
            merch = self.clean_merchant_name(m1.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch

        if "credited to your A/c" in message and "via IMPS" in message: return "IMPS Credit"

        if self.detect_is_card(message):
            if " at " in message.lower():
                m2 = re.search(r"at\s+([^.\n]+?)\s+on\s+your", message, re.I)
                if not m2: m2 = re.search(r"at\s+([^.\n]+?)\s+on\s+\d", message, re.I)
                if m2:
                    merch = self.clean_merchant_name(m2.group(1).strip())
                    if self.is_valid_merchant_name(merch):
                        merch = re.sub(r"\s+(limited|ltd|pvt\s+ltd|private\s+limited)$", "", merch, flags=re.I)
                        return merch.strip()

        if "e-mandate" in message.lower() or "payment of" in message.lower():
            m3 = re.search(r"payment of\s+[^.]+?\s+for\s+([^.\n]+?)\s+via\s+e-mandate", message, re.I)
            if m3:
                merch = self.clean_merchant_name(m3.group(1).strip())
                if self.is_valid_merchant_name(merch): return merch
            if re.search(r"payment via e-mandate\s+declined", message, re.I): return "E-Mandate Declined"

        if "VPA" in message.upper():
            m4 = re.search(r"to\s+VPA\s+([^\s]+?)(?:\.\s*Ref\s+No|\s*Ref\s+No|$)", message, re.I)
            if m4: return self._parse_upi_merchant(m4.group(1).strip())

        m5 = re.search(r"to\s+([^.\n]+?)(?:\.\s*Ref|Ref\s+No|$)", message, re.I)
        if m5 and "VPA" not in m5.group(1).upper():
            merch = self.clean_merchant_name(m5.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch

        if "you've received" in message.lower():
            m6 = re.search(r"It was sent by\s+([^.\n]+?)(?:\s+on|$)", message, re.I)
            if m6:
                snd = m6.group(1).strip()
                if re.match(r"^0+$", snd) or len(snd) <= 4: return "Bank Transfer"
                merch = self.clean_merchant_name(snd)
                if self.is_valid_merchant_name(merch): return merch

        m7 = re.search(r"from\s+([^.\n]+?)(?:\.\s*|$)", message, re.I)
        if m7:
            merch = self.clean_merchant_name(m7.group(1).strip())
            if self.is_valid_merchant_name(merch): return merch

        if any(kw in message.lower() for kw in ["cash deposit", "deposited", "cdm", "cash credited"]): return "Cash Deposit"
        
        return super().extract_merchant(message, sender)

    def _parse_upi_merchant(self, vpa: str) -> str:
        vparoot = vpa.split("@")[0].lower()
        map = {
            "indigo": "Indigo", "spicejet": "SpiceJet", "airasia": "AirAsia", "vistara": "Vistara", "airindia": "Air India",
            "uber": "Uber", "ola": "Ola", "rapido": "Rapido",
            "amazon": "Amazon", "flipkart": "Flipkart", "myntra": "Myntra", "meesho": "Meesho",
            "paytm": "Paytm", "bharatpe": "BharatPe", "phonepe": "PhonePe", "googlepay": "Google Pay", "gpay": "Google Pay",
            "swiggy": "Swiggy", "zomato": "Zomato",
            "netflix": "Netflix", "spotify": "Spotify", "hotstar": "Disney+ Hotstar", "disney": "Disney+ Hotstar", "prime": "Amazon Prime", "pvr": "PVR Inox", "inox": "PVR Inox", "bookmyshow": "BookMyShow", "bms": "BookMyShow",
            "jio": "Jio", "airtel": "Airtel", "vodafone": "Vi", "vi": "Vi", "bsnl": "BSNL",
            "irctc": "IRCTC", "redbus": "RedBus", "makemytrip": "MakeMyTrip", "mmt": "MakeMyTrip", "goibibo": "Goibibo", "oyo": "OYO", "airbnb": "Airbnb"
        }
        for k, v in map.items():
            if k in vparoot: return v
            
        if "razorpay" in vparoot or "razorp" in vparoot or "rzp" in vparoot:
            if "pvr" in vparoot: return "PVR"
            if "inox" in vparoot: return "PVR Inox"
            if "swiggy" in vparoot: return "Swiggy"
            if "zomato" in vparoot: return "Zomato"
            return "Online Payment"
        
        if any(k in vparoot for k in ["payu", "billdesk", "ccavenue"]): return "Online Payment"
        if vparoot.isdigit(): return "Individual"
        return vpa.strip()

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        if any(k in low for k in ["otp", "one time password", "verification code"]): return False
        
        # Mandate checks
        if "successfully created" in low or "initiated" in low: # overly simplified
            if any(k in low for k in ["mandate", "e-mandate"]): return False
        if ("e-mandate" in low or "payment of" in low) and "declined" in low: return False

        kw = ["sent via upi", "debited via upi", "credited", "withdrawn", "received", "transferred", "spent on your credit card", "credit card was successful", "payment of", "payment via e-mandate"]
        return any(k in low for k in kw) or super().is_transaction_message(message)

    def extract_account_last4(self, message: str) -> Optional[str]:
        if self.detect_is_card(message):
            m = re.search(r"(?:credit|debit)\s+card\s+ending\s+with\s+(\d{4})", message, re.I)
            if m: return m.group(1)
            m = re.search(r"card\s+XX\*\*?(\d{4})", message, re.I)
            if m: return m.group(1)
        return super().extract_account_last4(message)

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if re.search(r"has\s+received\s+Rs\s+[\d,.]+\s+from\s+your\s+A/c", message, re.I):
            if any(k in low for k in ["mutual fund", "gold", "sip", "investment"]): return TransactionType.INVESTMENT
            return TransactionType.EXPENSE
        
        if "received your payment" in low and "credit card" in low: return TransactionType.TRANSFER
        
        if "credit card" in low and any(k in low for k in ["spent", "was successful", "txn of"]): return TransactionType.CREDIT
        if ("e-mandate" in low or "payment of" in low) and "processed successfully" in low: return TransactionType.EXPENSE
        
        if any(k in low for k in ["sent via upi", "debited", "withdrawn", "paid"]): return TransactionType.EXPENSE
        if "spent" in low and "credit card" not in low: return TransactionType.EXPENSE
        
        if any(k in low for k in ["credited", "received", "deposited", "refund"]): return TransactionType.INCOME
        
        return super().extract_transaction_type(message)
