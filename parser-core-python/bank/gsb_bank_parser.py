import re
from .base_thailand_bank_parser import BaseThailandBankParser

class GSBBankParser(BaseThailandBankParser):
    """
    Government Savings Bank (GSB) parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Government Savings Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "GSB" or "GOVERNMENT SAVINGS" in up or "GOVT SAVINGS" in up
