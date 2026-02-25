from typing import List, Optional
from bank_parser import BankParser
from .hdfc_bank_parser import HDFCBankParser
from .sbi_bank_parser import SBIBankParser
from .saraswat_bank_parser import SaraswatBankParser
from .dbs_bank_parser import DBSBankParser
from .indian_bank_parser import IndianBankParser
from .federal_bank_parser import FederalBankParser
from .juspay_parser import JuspayParser
from .slice_parser import SliceParser
from .lazy_pay_parser import LazyPayParser
from .utkarsh_bank_parser import UtkarshBankParser
from .icici_bank_parser import ICICIBankParser
from .karnataka_bank_parser import KarnatakaBankParser
from .kerala_gramin_bank_parser import KeralaGraminBankParser
from .idbi_bank_parser import IDBIBankParser
from .jupiter_bank_parser import JupiterBankParser
from .axis_bank_parser import AxisBankParser
from .pnb_bank_parser import PNBBankParser
from .canara_bank_parser import CanaraBankParser
from .bank_of_baroda_parser import BankOfBarodaParser
from .bank_of_india_parser import BankOfIndiaParser
from .jio_payments_bank_parser import JioPaymentsBankParser
from .kotak_bank_parser import KotakBankParser
from .idfc_first_bank_parser import IDFCFirstBankParser
from .union_bank_parser import UnionBankParser
from .hsbc_bank_parser import HSBCBankParser
from .central_bank_of_india_parser import CentralBankOfIndiaParser
from .south_indian_bank_parser import SouthIndianBankParser
from .jk_bank_parser import JKBankParser
from .jio_pay_parser import JioPayParser
from .ippb_parser import IPPBParser
from .city_union_bank_parser import CityUnionBankParser
from .indian_overseas_bank_parser import IndianOverseasBankParser
from .airtel_payments_bank_parser import AirtelPaymentsBankParser
from .indusind_bank_parser import IndusIndBankParser
from .amex_bank_parser import AMEXBankParser
from .one_card_parser import OneCardParser
from .uco_bank_parser import UCOBankParser
from .au_bank_parser import AUBankParser
from .yes_bank_parser import YesBankParser
from .bandhan_bank_parser import BandhanBankParser
from .adcb_parser import ADCBParser
from .fab_parser import FABParser
from .emirates_nbd_parser import EmiratesNBDParser
from .liv_bank_parser import LivBankParser
from .citi_bank_parser import CitiBankParser
from .discover_card_parser import DiscoverCardParser
from .old_hickory_parser import OldHickoryParser
from .laxmi_bank_parser import LaxmiBankParser
from .cbe_bank_parser import CBEBankParser
from .everest_bank_parser import EverestBankParser
from .bancolombia_parser import BancolombiaParser
from .mashreq_bank_parser import MashreqBankParser
from .charles_schwab_parser import CharlesSchwabParser
from .navy_federal_parser import NavyFederalParser
from .adelfi_parser import AdelFiParser
from .priorbank_parser import PriorbankParser
from .alinma_bank_parser import AlinmaBankParser
from .nmb_bank_parser import NMBBankParser
from .siddhartha_bank_parser import SiddharthaBankParser
from .mpesa_tanzania_parser import MPesaTanzaniaParser
from .mpesa_parser import MPESAParser
from .selcom_pesa_parser import SelcomPesaParser
from .tigo_pesa_parser import TigoPesaParser
from .cib_egypt_parser import CIBEgyptParser
from .dhanlaxmi_bank_parser import DhanlaxmiBankParser
from .huntington_bank_parser import HuntingtonBankParser
from .standard_chartered_bank_parser import StandardCharteredBankParser
from .equitas_bank_parser import EquitasBankParser
from .telebirr_parser import TelebirrParser
from .zemen_bank_parser import ZemenBankParser
from .dashen_bank_parser import DashenBankParser
from .faysal_bank_parser import FaysalBankParser
from .melli_bank_parser import MelliBankParser
from .parsian_bank_parser import ParsianBankParser
from .bangkok_bank_parser import BangkokBankParser
from .kasikorn_bank_parser import KasikornBankParser
from .siam_commercial_bank_parser import SiamCommercialBankParser
from .krung_thai_bank_parser import KrungThaiBankParser
from .krungsri_bank_parser import KrungsriBankParser
from .ttb_bank_parser import TTBBankParser
from .gsb_bank_parser import GSBBankParser
from .baac_bank_parser import BAACBankParser
from .uob_thailand_parser import UOBThailandParser
from .cimb_thai_parser import CIMBThaiParser
from .ktc_credit_card_parser import KTCCreditCardParser

class BankParserFactory:
    """
    Factory for creating bank-specific parsers based on SMS sender.
    """

    _parsers: List[BankParser] = [
        HDFCBankParser(),
        SBIBankParser(),
        SaraswatBankParser(),
        DBSBankParser(),
        IndianBankParser(),
        FederalBankParser(),
        JuspayParser(),
        SliceParser(),
        LazyPayParser(),
        UtkarshBankParser(),
        ICICIBankParser(),
        KarnatakaBankParser(),
        KeralaGraminBankParser(),
        IDBIBankParser(),
        JupiterBankParser(),
        AxisBankParser(),
        PNBBankParser(),
        CanaraBankParser(),
        BankOfBarodaParser(),
        BankOfIndiaParser(),
        JioPaymentsBankParser(),
        KotakBankParser(),
        IDFCFirstBankParser(),
        UnionBankParser(),
        HSBCBankParser(),
        CentralBankOfIndiaParser(),
        SouthIndianBankParser(),
        JKBankParser(),
        JioPayParser(),
        IPPBParser(),
        CityUnionBankParser(),
        IndianOverseasBankParser(),
        AirtelPaymentsBankParser(),
        IndusIndBankParser(),
        AMEXBankParser(),
        OneCardParser(),
        UCOBankParser(),
        AUBankParser(),
        YesBankParser(),
        BandhanBankParser(),
        ADCBParser(),
        FABParser(),
        EmiratesNBDParser(),
        LivBankParser(),
        CitiBankParser(),
        DiscoverCardParser(),
        OldHickoryParser(),
        LaxmiBankParser(),
        CBEBankParser(),
        EverestBankParser(),
        BancolombiaParser(),
        MashreqBankParser(),
        CharlesSchwabParser(),
        NavyFederalParser(),
        AdelFiParser(),
        PriorbankParser(),
        AlinmaBankParser(),
        NMBBankParser(),
        SiddharthaBankParser(),
        MPesaTanzaniaParser(),
        MPESAParser(),
        SelcomPesaParser(),
        TigoPesaParser(),
        CIBEgyptParser(),
        DhanlaxmiBankParser(),
        HuntingtonBankParser(),
        StandardCharteredBankParser(),
        EquitasBankParser(),
        TelebirrParser(),
        ZemenBankParser(),
        DashenBankParser(),
        FaysalBankParser(),
        MelliBankParser(),
        ParsianBankParser(),
        BangkokBankParser(),
        KasikornBankParser(),
        SiamCommercialBankParser(),
        KrungThaiBankParser(),
        KrungsriBankParser(),
        TTBBankParser(),
        GSBBankParser(),
        BAACBankParser(),
        UOBThailandParser(),
        CIMBThaiParser(),
        KTCCreditCardParser()
    ]

    @classmethod
    def get_parser(cls, sender: str) -> Optional[BankParser]:
        """
        Returns the appropriate bank parser for the given sender.
        Returns None if no specific parser is found.
        """
        for parser in cls._parsers:
            if parser.can_handle(sender):
                return parser
        return None

    @classmethod
    def get_parser_by_name(cls, bank_name: str) -> Optional[BankParser]:
        """
        Returns the bank parser for the given bank name.
        Returns None if no specific parser is found.
        """
        for parser in cls._parsers:
            if parser.get_bank_name() == bank_name:
                return parser
        return None

    @classmethod
    def get_all_parsers(cls) -> List[BankParser]:
        """
        Returns all available bank parsers.
        """
        return cls._parsers

    @classmethod
    def is_known_bank_sender(cls, sender: str) -> bool:
        """
        Checks if the sender belongs to any known bank.
        """
        return any(parser.can_handle(sender) for parser in cls._parsers)
