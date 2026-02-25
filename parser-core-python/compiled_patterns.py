import re

class CompiledPatterns:
    class Amount:
        RS_PATTERN = re.compile(r"Rs\.?\s*([0-9,]+(?:\.\d{2})?)", re.IGNORECASE)
        INR_PATTERN = re.compile(r"INR\s*([0-9,]+(?:\.\d{2})?)", re.IGNORECASE)
        RUPEE_SYMBOL_PATTERN = re.compile(r"₹\s*([0-9,]+(?:\.\d{2})?)")
        ALL_PATTERNS = [RS_PATTERN, INR_PATTERN, RUPEE_SYMBOL_PATTERN]

    class Reference:
        GENERIC_REF = re.compile(
            r"(?:Ref|Reference|Txn|Transaction)(?:\s+No)?[:\s]+([A-Z0-9]+)",
            re.IGNORECASE
        )
        UPI_REF = re.compile(r"UPI[:\s]+([0-9]+)", re.IGNORECASE)
        REF_NUMBER = re.compile(r"Reference\s+Number[:\s]+([A-Z0-9]+)", re.IGNORECASE)
        ALL_PATTERNS = [GENERIC_REF, UPI_REF, REF_NUMBER]

    class Account:
        AC_WITH_MASK = re.compile(
            r"(?:A/c|Account|Acct)(?:\s+No)?\.?\s+(?:XX+|\*+)?(\d{3,4})",
            re.IGNORECASE
        )
        CARD_WITH_MASK = re.compile(r"Card\s+(?:XX+|\*+)?(\d{4})", re.IGNORECASE)
        ALL_PATTERNS = [AC_WITH_MASK, CARD_WITH_MASK]

    class Balance:
        AVL_BAL_RS = re.compile(r"(?:Bal|Balance|Avl Bal|Available Balance)[:\s]+Rs\.?\s*([0-9,]+(?:\.\d{2})?)", re.IGNORECASE)
        AVL_BAL_INR = re.compile(r"(?:Bal|Balance|Avl Bal|Available Balance)[:\s]+INR\s*([0-9,]+(?:\.\d{2})?)", re.IGNORECASE)
        AVL_BAL_RUPEE = re.compile(r"(?:Bal|Balance|Avl Bal|Available Balance)[:\s]+₹\s*([0-9,]+(?:\.\d{2})?)", re.IGNORECASE)
        AVL_BAL_NO_CURRENCY = re.compile(r"(?:Bal|Balance|Avl Bal|Available Balance)[:\s]+([0-9,]+(?:\.\d{2})?)", re.IGNORECASE)
        UPDATED_BAL_RS = re.compile(r"(?:Updated Balance|Remaining Balance)[:\s]+Rs\.?\s*([0-9,]+(?:\.\d{2})?)", re.IGNORECASE)
        UPDATED_BAL_INR = re.compile(r"(?:Updated Balance|Remaining Balance)[:\s]+INR\s*([0-9,]+(?:\.\d{2})?)", re.IGNORECASE)
        ALL_PATTERNS = [AVL_BAL_RS, AVL_BAL_INR, AVL_BAL_RUPEE, AVL_BAL_NO_CURRENCY, UPDATED_BAL_RS, UPDATED_BAL_INR]

    class Merchant:
        TO_PATTERN = re.compile(r"to\s+([^\.\n]+?)(?:\s+on|\s+at|\s+Ref|\s+UPI)", re.IGNORECASE)
        FROM_PATTERN = re.compile(r"from\s+([^\.\n]+?)(?:\s+on|\s+at|\s+Ref|\s+UPI)", re.IGNORECASE)
        AT_PATTERN = re.compile(r"at\s+([^\.\n]+?)(?:\s+on|\s+Ref)", re.IGNORECASE)
        FOR_PATTERN = re.compile(r"for\s+([^\.\n]+?)(?:\s+on|\s+at|\s+Ref)", re.IGNORECASE)
        ALL_PATTERNS = [TO_PATTERN, FROM_PATTERN, AT_PATTERN, FOR_PATTERN]

    class HDFC:
        DLT_PATTERNS = [
            re.compile(r"^[A-Z]{2}-HDFCBK.*$"),
            re.compile(r"^[A-Z]{2}-HDFC.*$"),
            re.compile(r"^HDFC-[A-Z]+$"),
            re.compile(r"^[A-Z]{2}-HDFCB.*$")
        ]

        SALARY_PATTERN = re.compile(
            r"for\s+[^-]+-[^-]+-[^-]+\s+[A-Z]+\s+SALARY-([^\.\n]+)",
            re.IGNORECASE
        )
        SIMPLE_SALARY_PATTERN = re.compile(r"SALARY[- ]([^\.\n]+?)(?:\s+Info|$)", re.IGNORECASE)
        INFO_PATTERN = re.compile(r"Info:\s*(?:UPI/)?([^/\.\n]+?)(?:/|$)", re.IGNORECASE)
        VPA_WITH_NAME = re.compile(r"VPA\s+[^@\s]+@[^\s]+\s*\(([^)]+)\)", re.IGNORECASE)
        VPA_PATTERN = re.compile(r"VPA\s+([^@\s]+)@", re.IGNORECASE)
        SPENT_PATTERN = re.compile(r"at\s+([^\.\n]+?)\s+on\s+\d{2}", re.IGNORECASE)
        DEBIT_FOR_PATTERN = re.compile(r"debited\s+for\s+([^\.\n]+?)\s+on\s+\d{2}", re.IGNORECASE)
        MANDATE_PATTERN = re.compile(r"To\s+([^\n]+?)\s*(?:\n|\d{2}/\d{2})", re.IGNORECASE)

        REF_SIMPLE = re.compile(r"Ref\s+(\d{9,12})", re.IGNORECASE)
        UPI_REF_NO = re.compile(r"UPI\s+Ref\s+No\s+(\d{12})", re.IGNORECASE)
        REF_NO = re.compile(r"Ref\s+No\.?\s+([A-Z0-9]+)", re.IGNORECASE)
        REF_END = re.compile(
            r"(?:Ref|Reference)[:.\s]+([A-Z0-9]{6,})(?:\s*$|\s*Not\s+You)",
            re.IGNORECASE
        )

        ACCOUNT_DEPOSITED = re.compile(
            r"deposited\s+in\s+(?:HDFC\s+Bank\s+)?A/c\s+(?:XX+)?(\d+)",
            re.IGNORECASE
        )
        ACCOUNT_FROM = re.compile(r"from\s+(?:HDFC\s+Bank\s+)?A/c\s+(?:XX+)?(\d+)", re.IGNORECASE)
        ACCOUNT_SIMPLE = re.compile(r"HDFC\s+Bank\s+A/c\s+(\d+)", re.IGNORECASE)
        ACCOUNT_GENERIC = re.compile(r"A/c\s+(?:XX+)?(\d+)", re.IGNORECASE)

        AMOUNT_WILL_DEDUCT = re.compile(
            r"Rs\.?\s*([0-9,]+(?:\.\d{2})?)\s+will\s+be\s+deducted",
            re.IGNORECASE
        )
        DEDUCTION_DATE = re.compile(
            r"deducted\s+on\s+(\d{2}/\d{2}/\d{2}),?\s*\d{2}:\d{2}:\d{2}",
            re.IGNORECASE
        )
        MANDATE_MERCHANT = re.compile(r"For\s+([^\n]+?)\s+mandate", re.IGNORECASE)
        UMN_PATTERN = re.compile(r"UMN\s+([a-zA-Z0-9@]+)", re.IGNORECASE)

    class Cleaning:
        TRAILING_PARENTHESES = re.compile(r"\s*\(.*?\)\s*$")
        REF_NUMBER_SUFFIX = re.compile(r"\s+Ref\s+No.*", re.IGNORECASE)
        DATE_SUFFIX = re.compile(r"\s+on\s+\d{2}.*")
        UPI_SUFFIX = re.compile(r"\s+UPI.*", re.IGNORECASE)
        TIME_SUFFIX = re.compile(r"\s+at\s+\d{2}:\d{2}.*")
        TRAILING_DASH = re.compile(r"\s*-\s*$")
        PVT_LTD = re.compile(r"(\s+PVT\.?\s*LTD\.?|\s+PRIVATE\s+LIMITED)$", re.IGNORECASE)
        LTD = re.compile(r"(\s+LTD\.?|\s+LIMITED)$", re.IGNORECASE)

    class Currency:
        ISO_CODE = re.compile(r"[A-Z]{3}")
        @staticmethod
        def SPECIFIC_ISO(code):
            return re.compile(code, re.IGNORECASE)
        COMMON_CURRENCIES = re.compile(r"(?:INR|Rs\.?|₹|USD|EUR|GBP|AED|SAR)", re.IGNORECASE)

    class Date:
        DD_MM_YY = re.compile(r"\d{1,2}/\d{1,2}/\d{2}")
        DD_MM_YYYY = re.compile(r"\d{1,2}/\d{1,2}/\d{4}")
        DD_MMM_YY = re.compile(r"\d{1,2}-[A-Za-z]{3}-\d{2}", re.IGNORECASE)
        DD_MM_YYYY_DASH = re.compile(r"\d{1,2}-\d{1,2}-\d{4}")

    class Time:
        HH_MM_SS = re.compile(r"\d{1,2}:\d{2}:\d{2}")
        HH_MM = re.compile(r"\d{1,2}:\d{2}")
