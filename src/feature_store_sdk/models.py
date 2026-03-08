"""
models.py
---------
Data models for parsed SMS features, organized by classified category.
Each model is a dataclass representing the structured output of parsing
a single SMS. These are the backbone for derived features downstream.

Flow:  raw SMS → tagger (classify) → category parser → data model → derived features
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import re


def _to_snake(value: str) -> str:
    """Convert a space/hyphen-delimited string to snake_case."""
    s = value.strip()
    s = re.sub(r'[/\-\s]+', '_', s)
    # insert underscore before uppercase runs followed by lowercase
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.lower()


# Fields whose string values should be snake_case-standardized
_STANDARDIZE_FIELDS = frozenset({
    "traffic_type", "sms_category", "txn_type", "txn_subtype",
    "financial_product", "txn_channel", "context",
    "event_type", "insurance_type", "asset_type",
    "bill_type", "promo_type", "offered_product",
    "alert_type", "action_taken", "otp_for",
})


def _clean_dict(d: dict) -> dict:
    """Strip None-valued keys and snake_case-standardize enum-like string fields."""
    cleaned = {}
    for k, v in d.items():
        if v is None:
            continue
        if k in _STANDARDIZE_FIELDS and isinstance(v, str) and v:
            v = _to_snake(v)
        cleaned[k] = v
    return cleaned


# ===========================================================================
# BASE
# ===========================================================================
@dataclass
class SMSBase:
    """Common fields extracted from every SMS regardless of category."""
    raw_body: str = ""
    sender_address: str = ""
    entity_name: str = "unknown"
    header_code: Optional[str] = None
    traffic_type: str = "GENERAL"
    sms_category: str = "Other"
    occurrence_tag: str = ""
    alphabetical_tag: str = ""
    tag_count: int = 0
    timestamp: Optional[str] = None

    def to_dict(self) -> dict:
        return _clean_dict(asdict(self))


# ===========================================================================
# TRANSACTIONS
# ===========================================================================
@dataclass
class TransactionParsed(SMSBase):
    """Parsed features from a transaction SMS (debit/credit/UPI/NEFT/card)."""
    sms_category: str = "Transactions"

    # Core transaction fields
    txn_type: Optional[str] = None          # Credit / Debit / Mandate / Unknown
    txn_subtype: Optional[str] = None       # UPI Transfer / Card Purchase / Salary Credit / EMI/Loan / Refund etc.
    amount: Optional[float] = None
    balance: Optional[float] = None
    avl_limit: Optional[float] = None       # credit card available limit
    last_bill: Optional[float] = None       # credit card last bill amount

    # Instrument identification
    account_number: Optional[str] = None    # last 3-4 digits
    card_number: Optional[str] = None       # last 4 digits
    financial_product: Optional[str] = None # Bank Account / Credit Card / Wallet / Loans

    # Channel & routing
    txn_channel: Optional[str] = None       # UPI / NEFT / IMPS / Card / Wallet / Net Banking / Generic
    reference_number: Optional[str] = None

    # Counterparty
    payer: Optional[str] = None
    payee: Optional[str] = None

    # Context flags
    context: Optional[str] = None           # Refund/Reversal / Bill Payment / Mandate Activity / General Transaction
    mandate_flag: bool = False
    is_salary: bool = False


# ===========================================================================
# LENDING
# ===========================================================================
@dataclass
class LendingParsed(SMSBase):
    """Parsed features from a lending/loan/EMI SMS."""
    sms_category: str = "Lending"

    # Loan identification
    loan_account: Optional[str] = None      # masked account number
    lender_name: Optional[str] = None       # bank or NBFC name

    # Event type
    event_type: Optional[str] = None        # Disbursement / EMI Due / EMI Paid / Overdue / Approved / Rejected / Limit Change

    # Financial details
    emi_amount: Optional[float] = None
    principal: Optional[float] = None
    interest: Optional[float] = None
    outstanding: Optional[float] = None
    sanctioned_amount: Optional[float] = None
    credit_limit: Optional[float] = None

    # Schedule
    due_date: Optional[str] = None
    dpd: Optional[int] = None               # days past due (0 = on time)

    # Flags
    is_overdue: bool = False
    is_emi: bool = False
    is_disbursement: bool = False


# ===========================================================================
# INSURANCE
# ===========================================================================
@dataclass
class InsuranceParsed(SMSBase):
    """Parsed features from an insurance SMS."""
    sms_category: str = "Insurance"

    # Entity & product
    insurer_name: Optional[str] = None      # LIC / Niva Bupa / HDFC Life etc.
    insurance_type: Optional[str] = None    # Life / Health / Motor / Term

    # Policy details
    policy_number: Optional[str] = None
    sum_assured: Optional[float] = None

    # Event
    event_type: Optional[str] = None        # Renewal / Premium Due / New Policy / Claim / Payout / Wellness

    # Financial
    premium_amount: Optional[float] = None
    claim_amount: Optional[float] = None

    # Schedule
    due_date: Optional[str] = None
    renewal_date: Optional[str] = None

    # Beneficiary (for household detection)
    beneficiary_name: Optional[str] = None


# ===========================================================================
# INVESTMENTS
# ===========================================================================
@dataclass
class InvestmentParsed(SMSBase):
    """Parsed features from an investment SMS (MF/SIP/stocks/gold)."""
    sms_category: str = "Investments"

    # Asset identification
    asset_type: Optional[str] = None        # Mutual Fund / Gold / Stock / Demat
    fund_name: Optional[str] = None         # scheme or stock name
    platform: Optional[str] = None          # Groww / Zerodha / CAMS etc.

    # Event
    event_type: Optional[str] = None        # SIP Debit / Units Allotted / Redemption / Dividend / Registration

    # Financial
    amount: Optional[float] = None
    nav: Optional[float] = None
    units: Optional[float] = None

    # Flags
    is_sip: bool = False
    is_redemption: bool = False


# ===========================================================================
# EPFO
# ===========================================================================
@dataclass
class EPFOParsed(SMSBase):
    """Parsed features from an EPFO/PF SMS."""
    sms_category: str = "EPFO"

    uan: Optional[str] = None
    event_type: Optional[str] = None        # Contribution / Withdrawal / Passbook Update / KYC

    # Financial
    employee_share: Optional[float] = None
    employer_share: Optional[float] = None
    total_balance: Optional[float] = None

    # Period
    contribution_month: Optional[str] = None


# ===========================================================================
# UTILITY BILLS
# ===========================================================================
@dataclass
class UtilityBillParsed(SMSBase):
    """Parsed features from a utility bill SMS."""
    sms_category: str = "Utility Bills"

    # Bill identification
    bill_type: Optional[str] = None         # Electricity / Water / Gas / Mobile / Broadband / DTH
    provider: Optional[str] = None          # BSNL / Jio / Airtel / BESCOM etc.
    consumer_number: Optional[str] = None

    # Financial
    bill_amount: Optional[float] = None
    due_date: Optional[str] = None

    # Status
    is_payment_confirmation: bool = False
    is_due_reminder: bool = False


# ===========================================================================
# PROMOTIONS
# ===========================================================================
@dataclass
class PromotionParsed(SMSBase):
    """Parsed features from a promotional/offer SMS."""
    sms_category: str = "Promotions"

    promo_type: Optional[str] = None        # Credit Card Offer / Loan Offer / Cashback / Discount
    offered_product: Optional[str] = None   # product being promoted
    offered_limit: Optional[float] = None   # pre-approved limit if mentioned
    merchant: Optional[str] = None          # merchant running the offer

    has_cta: bool = False                   # contains call-to-action (apply now, click here)
    has_expiry: bool = False                # contains validity/expiry date


# ===========================================================================
# ORDERS & DELIVERY
# ===========================================================================
@dataclass
class OrderParsed(SMSBase):
    """Parsed features from an order/delivery SMS."""
    sms_category: str = "Orders"

    merchant: Optional[str] = None          # Amazon / Flipkart / Swiggy etc.
    order_id: Optional[str] = None

    event_type: Optional[str] = None        # Placed / Shipped / Out for Delivery / Delivered / Cancelled / Returned
    amount: Optional[float] = None

    # Delivery
    delivery_partner: Optional[str] = None  # Ekart / Delhivery / BlueDart
    estimated_date: Optional[str] = None


# ===========================================================================
# SECURITY ALERTS
# ===========================================================================
@dataclass
class SecurityAlertParsed(SMSBase):
    """Parsed features from a security/fraud alert SMS."""
    sms_category: str = "Security Alert"

    alert_type: Optional[str] = None        # Card Block / UPI Block / Fraud Report / Suspicious Activity
    affected_instrument: Optional[str] = None  # card/account number affected
    action_taken: Optional[str] = None      # Blocked / Reported / Under Review


# ===========================================================================
# OTP (minimal - mainly for filtering)
# ===========================================================================
@dataclass
class OTPParsed(SMSBase):
    """Parsed features from an OTP SMS."""
    sms_category: str = "OTP"

    otp_for: Optional[str] = None           # login / transaction / registration
    validity_minutes: Optional[int] = None
    platform: Optional[str] = None          # which service sent the OTP


# ===========================================================================
# CATEGORY → MODEL MAPPING
# ===========================================================================
CATEGORY_MODEL_MAP = {
    "transactions": TransactionParsed,
    "lending": LendingParsed,
    "insurance": InsuranceParsed,
    "investments": InvestmentParsed,
    "epfo": EPFOParsed,
    "utility_bills": UtilityBillParsed,
    "promotions": PromotionParsed,
    "orders": OrderParsed,
    "security_alert": SecurityAlertParsed,
    "otp": OTPParsed,
}


def get_model_for_category(category: str):
    """Returns the dataclass type for a given SMS category."""
    return CATEGORY_MODEL_MAP.get(category, SMSBase)


def get_empty_model(category: str) -> dict:
    """Returns a dict with all fields for a category initialized to defaults."""
    model_cls = get_model_for_category(category)
    return _clean_dict(asdict(model_cls()))
