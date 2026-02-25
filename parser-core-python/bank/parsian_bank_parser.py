import re
from .base_iranian_bank_parser import BaseIranianBankParser

class ParsianBankParser(BaseIranianBankParser):
    """
    Parsian Bank parser for Iranian banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Parsian Bank"

    def can_handle(self, sender: str) -> bool:
        return sender.upper() in ["PARSIANBANK", "PARSIAN", "PARSIAN BANK", "PERSIANBANK", "PERSIAN"]
