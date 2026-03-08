"""
parsers
-------
Category-specific SMS parsers. Each module exposes a ``parse_*_model``
function with signature ``(body, address, base_fields) -> dataclass``.
"""

from .transaction import parse_transaction_model
from .insurance import parse_insurance_model
from .investment import parse_investment_model
from .promotion import parse_promotion_model
from .lending import parse_lending_model
from .epfo import parse_epfo_model
from .utility import parse_utility_model
from .order import parse_order_model
from .security import parse_security_model
from .otp import parse_otp_model
