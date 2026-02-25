import re
from .base_thailand_bank_parser import BaseThailandBankParser

class SiamCommercialBankParser(BaseThailandBankParser):
    """
    Siam Commercial Bank (SCB) parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Siam Commercial Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "SCB" or "SIAM COMMERCIAL" in up or "SIAMCOMMERCIAL" in up
