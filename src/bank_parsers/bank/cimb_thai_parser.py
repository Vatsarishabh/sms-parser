import re
from .base_thailand_bank_parser import BaseThailandBankParser

class CIMBThaiParser(BaseThailandBankParser):
    """
    CIMB Thai Bank parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "CIMB Thai"

    def can_handle(self, sender: str) -> bool:
        upper = sender.upper()
        return upper == "CIMB" or "CIMB THAI" in upper or "CIMBTHAI" in upper
