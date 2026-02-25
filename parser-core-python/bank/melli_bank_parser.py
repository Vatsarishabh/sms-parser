import re
from base_iranian_bank_parser import BaseIranianBankParser

class MelliBankParser(BaseIranianBankParser):
    """
    Bank Melli parser for Iranian banking SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Melli Bank"

    def can_handle(self, sender: str) -> bool:
        return sender.upper() in ["+98700717", "MELLI", "MELLIBANK", "MELLI BANK", "BANK MELLI", "BANKMELLI"]
