import os
import glob
from pathlib import Path

# Files to patch
target_files = glob.glob('backend/data_pipeline/validate_*.py') + \
               glob.glob('backend/data_pipeline/verify_*.py') + \
               glob.glob('backend/data_pipeline/audit_*.py') + \
               glob.glob('backend/data_pipeline/test_*.py') + \
               glob.glob('backend/data_pipeline/week15_quality_monitor.py')

replacements = [
    ("EXPECTED_COMPANIES = 50", "EXPECTED_COMPANIES = 100"),
    ("Expected 50 companies", "Expected 100 companies"),
    ("50-Stock Universe", "100-Stock Universe"),
    ("50-stock universe", "100-stock universe"),
    ("distinct_symbols != 50", "distinct_symbols != 100"),
    ("company_count != 50", "company_count != 100"),
    ("daily_symbols != 50", "daily_symbols != 100"),
    ("technical_symbols != 50", "technical_symbols != 100"),
    ("distinct_companies < 50", "distinct_companies < 100"),
    ("covered_companies < 50", "covered_companies < 100"),
    ("== 50", "== 100"),
    ("50 companies present", "100 companies present"),
    ("All 50 companies", "All 100 companies"),
    ("50 companies available", "100 companies available"),
    ("50-stock dataset", "100-stock dataset"),
    ("50 companies in the stock universe", "100 companies in the stock universe"),
    ("50/50 companies covered", "100/100 companies covered"),
    ("sector_total != 50", "sector_total != 100")
]

for file_path in target_files:
    if not os.path.exists(file_path):
        continue
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            modified = True
                
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {file_path}")
