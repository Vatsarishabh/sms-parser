import re
from .base_thailand_bank_parser import BaseThailandBankParser

class KasikornBankParser(BaseThailandBankParser):
    """
    Kasikorn Bank (KBank) parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Kasikorn Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "KBANK" or "KASIKORN" in up or "KASIKORNBANK" in up
