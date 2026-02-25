import re
from base_thailand_bank_parser import BaseThailandBankParser

class BangkokBankParser(BaseThailandBankParser):
    """
    Bangkok Bank (BBL) parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Bangkok Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "BBL" or "BANGKOK BANK" in up or "BANGKOKBANK" in up
