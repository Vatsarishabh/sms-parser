from enum import Enum

class TransactionType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    CREDIT = "CREDIT"
    TRANSFER = "TRANSFER"
    INVESTMENT = "INVESTMENT"
    BALANCE_UPDATE = "BALANCE_UPDATE"
