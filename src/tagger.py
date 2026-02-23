import pandas as pd
import re
import os

# 1. Self-contained Category Configuration
CATEGORY_KEYWORDS = {
    "Transactions": [
        r"debited", r"credited", r"txn", r"transaction", r"spent",
        r"withdrawn", r"deposited", r"upi", r"imps", r"neft", r"rtgs",
        r"wallet", r"card", r"atm", r"purchase", r"payment to"
    ],
    "Lending": [
        r"loan", r"emi", r"repayment", r"overdue", r"due amount",
        r"credit limit", r"disbursed", r"interest charged", r"sanctioned"
    ],
    "Insurance": [
        r"insurance", r"policy", r"premium", r"sum assured",
        r"lic", r"renewal", r"claim"
    ],
    "Investments": [
        r"mutual fund", r"sip", r"nav", r"portfolio",
        r"demat", r"dividend", r"nfo", r"stock", r"equity"
    ],
    "EPFO": [
        r"epfo", r"pf contribution", r"uan", r"provident fund", r"pension"
    ],
    "Utility Bills": [
        r"electricity bill", r"water bill", r"gas bill",
        r"mobile bill", r"broadband", r"recharge",
        r"bill payment", r"due date"
    ]
}
BANK_MAPPING = {
    r"CANBNK|CNRBNK": "Canara Bank",
    r"AXISBK": "Axis Bank",
    r"HDFCBK|HDFCBN": "HDFC Bank",
    r"ICICIB|ICICBK": "ICICI Bank",
    r"SBIBNK|SBIINB": "State Bank of India",
    r"KOTAKB|KKBANK": "Kotak Mahindra Bank",
    r"IDFCBK": "IDFC First Bank",
    r"IDBIBK": "IDBI Bank",
    r"INDBNK": "Indian Bank",
    r"IOBANK": "Indian Overseas Bank",
    r"PNBSMS|PNBBNK": "Punjab National Bank",
    r"BARODA|BOBTXN": "Bank of Baroda",
    r"YESBNK|YESBNF": "Yes Bank",
    r"RBLBNK|RBLCRD": "RBL Bank",
    r"UCOBNK": "UCO Bank",
    r"UBINBK|UNIONB": "Union Bank of India",
    r"CBINBK|CENTBK": "Central Bank of India",
    r"PSBANK": "Punjab & Sind Bank",
    r"FEDBNK": "Federal Bank",
    r"SOUTHB|SIBLTD": "South Indian Bank",
    r"DCBBNK": "DCB Bank",
    r"KARBNK": "Karnataka Bank",
    r"TMBANK": "Tamilnad Mercantile Bank",
    r"TNSCGB": "TNSC Bank",
    r"INDUSB|INDUSL": "IndusInd Bank",
    r"DBSSMS|DBSBIN": "DBS Bank",
    r"SCBANK": "Standard Chartered Bank",
    r"HSBCIN": "HSBC Bank",
    r"CITIBK": "Citi Bank",
    r"AUFINB": "AU Small Finance Bank",
    r"EQUITB": "Equitas Small Finance Bank",
    r"ESAFBK": "ESAF Small Finance Bank",
    r"JKBANK": "J&K Bank",
    r"BANDHN": "Bandhan Bank",
    r"NKGSMS": "NKGSB Co-op Bank",
    r"KVBLTD": "Karur Vysya Bank"
}

def identify_bank(address):
    """Identifies the bank name from the sender address code."""
    if not isinstance(address, str):
        return "Non-Banking"
    
    address = address.upper()
    for pattern, bank_name in BANK_MAPPING.items():
        if re.search(pattern, address):
            return bank_name
    return "Non-Banking"

def tag_message(text):
    """
    Analyzes the message text and returns the best matching category.
    """
    if not isinstance(text, str) or text.strip() == "":
        return "Unknown"
    
    text = text.lower()
    
    # Store match counts for each category
    match_counts = {}
    
    for category, patterns in CATEGORY_KEYWORDS.items():
        count = 0
        for pattern in patterns:
            if re.search(pattern, text):
                count += 1
        if count > 0:
            match_counts[category] = count
            
    # Return the category with the most keyword matches
    if match_counts:
        # Sort by count descending and return the top one
        return max(match_counts, key=match_counts.get)
    
    return "Other"

def process_sms_df(df):
    """
    Tags a dataframe with bank names and categories.
    """
    df = df.copy()
    
    # Try to identify the columns
    msg_col = None
    addr_col = None
    
    for col in df.columns:
        if col.lower() in ['body', 'message', 'text']:
            msg_col = col
        if col.lower() in ['address', 'sender_id']:
            addr_col = col
            
    if not msg_col:
        print("Error: Could not find SMS body column.")
        return df
        
    print(f"Processing SMS in '{msg_col}' using address in '{addr_col}'...")
    
    # Apply bank identification and tagging
    if addr_col:
        df['bank_name'] = df[addr_col].apply(identify_bank)
    else:
        df['bank_name'] = "Unknown"
        
    df['sms_category'] = df[msg_col].apply(tag_message)
    
    return df

if __name__ == "__main__":
    # process_sms_df()
    pass