from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

class MandateInfo(ABC):
    """
    Common interface for mandate information across all banks.
    This allows standardized handling of subscription/mandate data
    from different banks while maintaining bank-specific implementations.
    """
    
    @property
    @abstractmethod
    def amount(self) -> Decimal:
        """The amount that will be charged"""
        pass

    @property
    @abstractmethod
    def next_deduction_date(self) -> Optional[str]:
        """The next deduction date in string format"""
        pass

    @property
    @abstractmethod
    def merchant(self) -> str:
        """The merchant/service name"""
        pass

    @property
    @abstractmethod
    def umn(self) -> Optional[str]:
        """Unique Mandate Number (if available)"""
        pass

    @property
    def date_format(self) -> str:
        """The date format used by this bank for parsing next_deduction_date"""
        return "dd/MM/yy"
