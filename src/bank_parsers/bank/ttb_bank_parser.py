import re
from .base_thailand_bank_parser import BaseThailandBankParser

class TTBBankParser(BaseThailandBankParser):
    """
    TTB (TMBThanachart Bank) parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "TTB"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "TTB" or "TMBTHANACHART" in up or "TMB" in up
