import os
import re

bank_dir = os.path.join(os.path.dirname(__file__), "bank")

files_fixed = 0
for fname in os.listdir(bank_dir):
    if not fname.endswith(".py"):
        continue
    fpath = os.path.join(bank_dir, fname)
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    # Fix bank_parser relative import
    # Some might use from ..bank_parser import ..., some might have different spacing
    new_content = re.sub(r"from \.\.bank_parser import", "from .bank_parser import", content)
    
    # Also handle the user's manual change if they want consistency
    new_content = re.sub(r"from bank_parser import", "from .bank_parser import", new_content)

    if new_content != content:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_content)
        files_fixed += 1
        print(f"Fixed: {fname}")

print(f"Total files fixed: {files_fixed}")
