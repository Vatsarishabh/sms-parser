import re
from .base_thailand_bank_parser import BaseThailandBankParser

class KrungsriBankParser(BaseThailandBankParser):
    """
    Krungsri (Bank of Ayudhya - BAY) parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Krungsri"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "BAY" or "KRUNGSRI" in up or "AYUDHYA" in up
