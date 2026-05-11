#!/usr/bin/env python3
"""
Apply company name corrections to the merged CSV.
Usage:
  1. Edit COMPANY_NAME_CORRECTIONS below with the correct Chinese names
  2. Run: python3 scripts/apply_name_corrections.py
"""

from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / 'data' / 'worldbank_idb_aiddata_cdb_merged.csv'

# EDIT THIS DICT with correct Chinese names based on your research
# English name (as it appears in CSV) -> Chinese name
COMPANY_NAME_CORRECTIONS = {
    # TODO: You can paste the correct Chinese names here
    # Example format:
    # 'POWERCHINA JIANGXI ELECTRIC POWER CONSTRUCTION COMPANY LIMITED': '国家电网有限公司江西分公司',
    # 'China MEHECO Corporation': '中国医药对外贸易总公司',
}


def apply_corrections():
    df = pd.read_csv(MERGED, dtype=str)
    
    print(f"Loaded {len(df)} rows")
    print(f"Companies to correct: {len(COMPANY_NAME_CORRECTIONS)}")
    print()

    applied = 0
    for en_name, correct_zh in COMPANY_NAME_CORRECTIONS.items():
        # Find all rows with this English name
        mask = df['winning_firm_name'] == en_name
        count = mask.sum()
        if count > 0:
            df.loc[mask, 'winning_firm_name_zh'] = correct_zh
            print(f"✓ {en_name[:50]}")
            print(f"  → {correct_zh}")
            print(f"  Applied to {count} row(s)")
            print()
            applied += count

    if applied > 0:
        # Save and export
        df.to_csv(MERGED, index=False, encoding='utf-8-sig')
        print(f"\n✓ Applied {applied} corrections to {MERGED}")
        
        # Export both formats
        try:
            import subprocess
            subprocess.run(['python3', 'scripts/save_both_formats.py', str(MERGED)], check=False)
            print("✓ Exported CSV and Excel copies")
        except Exception as e:
            print(f"Warning: Could not export copies: {e}")
    else:
        print("No corrections were applied. Add entries to COMPANY_NAME_CORRECTIONS dict.")


if __name__ == '__main__':
    apply_corrections()
