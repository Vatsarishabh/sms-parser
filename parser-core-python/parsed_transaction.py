from decimal import Decimal, ROUND_HALF_UP
import hashlib
from typing import Optional
from transaction_type import TransactionType

class ParsedTransaction:
    def __init__(
        self,
        amount: Decimal,
        type: TransactionType,
        sms_body: str,
        sender: str,
        timestamp: int,
        bank_name: str,
        merchant: Optional[str] = None,
        reference: Optional[str] = None,
        account_last4: Optional[str] = None,
        balance: Optional[Decimal] = None,
        credit_limit: Optional[Decimal] = None,
        transaction_hash: Optional[str] = None,
        is_from_card: bool = False,
        currency: str = "INR",
        from_account: Optional[str] = None,
        to_account: Optional[str] = None
    ):
        self.amount = amount
        self.type = type
        self.merchant = merchant
        self.reference = reference
        self.account_last4 = account_last4
        self.balance = balance
        self.credit_limit = credit_limit
        self.sms_body = sms_body
        self.sender = sender
        self.timestamp = timestamp
        self.bank_name = bank_name
        self.transaction_hash = transaction_hash
        self.is_from_card = is_from_card
        self.currency = currency
        self.from_account = from_account
        self.to_account = to_account

    def generate_transaction_id(self) -> str:
        normalized_amount = self.amount.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
        
        # Use SMS body hash for reliable deduplication
        sms_body_hash = hashlib.md5(self.sms_body.encode()).hexdigest()[:16]
        
        data = f"{self.sender}|{normalized_amount}|{sms_body_hash}"
        return hashlib.md5(data.encode()).hexdigest()
