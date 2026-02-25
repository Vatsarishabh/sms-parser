import re
from .base_thailand_bank_parser import BaseThailandBankParser

class UOBThailandParser(BaseThailandBankParser):
    """
    UOB Thailand parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "UOB Thailand"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "UOB" or "UOB THAILAND" in up or "UOBTHAILAND" in up
