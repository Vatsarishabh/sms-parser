from typing import List, Optional
from bank_parser import BankParser

class BankParserRegistry:
    def __init__(self, parsers: List[BankParser]):
        self.parsers = parsers

    def get_parser(self, sender: str) -> Optional[BankParser]:
        for parser in self.parsers:
            if parser.can_handle(sender):
                return parser
        return None

    def all(self) -> List[BankParser]:
        return self.parsers
