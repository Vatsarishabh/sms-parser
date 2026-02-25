import re
from base_thailand_bank_parser import BaseThailandBankParser

class BAACBankParser(BaseThailandBankParser):
    """
    Bank for Agriculture and Agricultural Cooperatives (BAAC) parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "BAAC"

    def can_handle(self, sender: str) -> bool:
        upper = sender.upper()
        return upper == "BAAC" or "AGRICULTURE" in upper
