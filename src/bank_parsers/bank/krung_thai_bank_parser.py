import re
from .base_thailand_bank_parser import BaseThailandBankParser

class KrungThaiBankParser(BaseThailandBankParser):
    """
    Krungthai Bank (KTB) parser for Thai banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Krungthai Bank"

    def can_handle(self, sender: str) -> bool:
        up = sender.upper()
        return up == "KTB" or "KRUNGTHAI" in up or "KRUNG THAI" in up
