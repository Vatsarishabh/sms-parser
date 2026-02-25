import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from bank_parser import BankParser
from transaction_type import TransactionType

class BancolombiaParser(BankParser):
    """
    Parser for Bancolombia (Colombian bank) SMS messages.
    """

    def get_bank_name(self) -> str:
        return "Bancolombia"

    def can_handle(self, sender: str) -> bool:
        return sender in ["87400", "85540"]

    def get_currency(self) -> str:
        return "COP"

    def is_transaction_message(self, message: str) -> bool:
        low = message.lower()
        return any(kw in low for kw in ["transferiste", "compraste", "pagaste", "recibiste"])

    def extract_amount(self, message: str) -> Optional[Decimal]:
        match = re.search(r"(Transferiste|Compraste|Pagaste|Recibiste)\s+\$?([0-9.,]+)", message, re.IGNORE_CASE)
        if match:
            raw = match.group(2).replace(".", "").replace(",", ".").replace("$", "").strip()
            try: return Decimal(raw)
            except (InvalidOperation, ValueError): pass
        return None

    def extract_transaction_type(self, message: str) -> Optional[TransactionType]:
        low = message.lower()
        if any(kw in low for kw in ["transferiste", "compraste", "pagaste"]): return TransactionType.EXPENSE
        if "recibiste" in low: return TransactionType.INCOME
        return None

    def extract_merchant(self, message: str, sender: str) -> Optional[str]:
        low = message.lower()
        if "transferiste" in low: return "Transferencia"
        if "compraste" in low: return "Compra"
        if "pagaste" in low: return "Pago"
        if "recibiste" in low: return "Dinero recibido"
        return "Bancolombia"
