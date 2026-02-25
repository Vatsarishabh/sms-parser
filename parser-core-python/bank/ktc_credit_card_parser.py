import re
from typing import Optional
from base_thailand_bank_parser import BaseThailandBankParser
from parsed_transaction import ParsedTransaction
from transaction_type import TransactionType

class KTCCreditCardParser(BaseThailandBankParser):
    """
    KTC Credit Card parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "KTC"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "KTC" or "KRUNGTHAI CARD" in up

    def parse(self, sms_body: str, sender: str, timestamp: int) -> Optional[ParsedTransaction]:
        parsed = super().parse(sms_body, sender, timestamp)
        if not parsed: return None
        
        parsed.type = parsed.type or TransactionType.CREDIT
        parsed.isFromCard = True
        parsed.creditLimit = self.extract_available_limit(sms_body)
        return parsed
