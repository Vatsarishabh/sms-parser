import csv
import sys
import os
import importlib.util
import types

# ── Bootstrap ─────────────────────────────────────────────────────────────────
# The folder is named "parser-core-python" (hyphen → invalid Python identifier).
# We load it manually via importlib and register it in sys.modules under the
# alias "parser_core_python" so that all internal relative imports work.
_THIS_DIR   = os.path.dirname(os.path.realpath(__file__))   # …/parser-core-python
_PARENT_DIR = os.path.dirname(_THIS_DIR)                    # …/Regex Notebooks
_PKG_ALIAS  = "parser_core_python"

if _PKG_ALIAS not in sys.modules:
    # Register the top-level package
    spec = importlib.util.spec_from_file_location(
        _PKG_ALIAS,
        os.path.join(_THIS_DIR, "__init__.py"),
        submodule_search_locations=[_THIS_DIR],
    )
    pkg = importlib.util.module_from_spec(spec)
    pkg.__path__ = [_THIS_DIR]
    pkg.__package__ = _PKG_ALIAS
    sys.modules[_PKG_ALIAS] = pkg
    spec.loader.exec_module(pkg)

from parser_core_python.bank.bank_parser_factory import BankParserFactory
# ─────────────────────────────────────────────────────────────────────────────


input_file = os.path.join(os.path.dirname(__file__), '..', 'sms_inbox_rahul.csv')
output_file = os.path.join(os.path.dirname(__file__), '..', 'sms_parsing_output_data_rahul.csv')

def process_sms_data(input_path, output_path):
    print(f"Reading from {input_path}")
    
    parsed_count = 0
    total_count = 0

    with open(input_path, 'r', encoding='utf-8') as f_in, open(output_path, 'w', encoding='utf-8', newline='') as f_out:
        reader = csv.DictReader(f_in)
        
        # Extend headers to include parsed information
        fieldnames = reader.fieldnames + [
            'parsed_amount', 'parsed_type', 'merchant', 'reference', 
            'account_last4', 'balance', 'credit_limit', 'bank_name', 
            'is_from_card', 'currency'
        ]
        
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            total_count += 1
            sender = row.get('address', '')
            body = row.get('body', '')
            timestamp_str = row.get('date', '0')
            
            try:
                timestamp = int(timestamp_str)
            except ValueError:
                timestamp = 0
                
            parser = BankParserFactory.get_parser(sender)
            
            if parser:
                parsed_txn = parser.parse(body, sender, timestamp)
                if parsed_txn:
                    row['parsed_amount'] = parsed_txn.amount if parsed_txn.amount is not None else ''
                    row['parsed_type'] = parsed_txn.type.value if hasattr(parsed_txn.type, 'value') else parsed_txn.type
                    row['merchant'] = parsed_txn.merchant if parsed_txn.merchant else ''
                    row['reference'] = parsed_txn.reference if parsed_txn.reference else ''
                    row['account_last4'] = parsed_txn.account_last4 if parsed_txn.account_last4 else ''
                    row['balance'] = parsed_txn.balance if parsed_txn.balance is not None else ''
                    row['credit_limit'] = parsed_txn.credit_limit if parsed_txn.credit_limit is not None else ''
                    row['bank_name'] = parsed_txn.bank_name if parsed_txn.bank_name else ''
                    row['is_from_card'] = parsed_txn.is_from_card
                    row['currency'] = parsed_txn.currency if parsed_txn.currency else ''
                    
                    parsed_count += 1
                
            writer.writerow(row)

    print(f"Parsing complete. Processed {total_count} messages, parsed {parsed_count} transactions.")
    print(f"Output saved to {output_path}")

if __name__ == "__main__":
    process_sms_data(input_file, output_file)
