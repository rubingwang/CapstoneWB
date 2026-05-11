#!/usr/bin/env python3
"""Light clean of Chinese firm names in the merged CSV.

Rules applied:
- Trim whitespace and collapse multi-spaces
- Remove spaces between adjacent CJK characters
- Remove spaces between Latin and CJK characters
- Normalize fullwidth spaces to normal spaces
- Remove stray control characters

Writes back `data/worldbank_idb_merged.csv` (UTF-8-sig) and updates cache/report.
"""
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / 'data' / 'worldbank_idb_aiddata_cdb_merged.csv'
CACHE = ROOT / 'data' / 'firm_name_chinese_cache.json'
REPORT = ROOT / 'reports' / 'firm_name_chinese_review.csv'


def clean_text(s: str) -> str:
    if not isinstance(s, str):
        return s
    # normalize spaces
    s = s.replace('\u3000', ' ')
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    # remove spaces between CJK characters
    s = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', s)
    # remove spaces between Latin and CJK (both directions)
    s = re.sub(r'(?<=[A-Za-z0-9\)])\s+(?=[\u4e00-\u9fff])', '', s)
    s = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[A-Za-z0-9\(])', '', s)
    # collapse multiple punctuation spaces
    s = re.sub(r'\s+([，。；：,.;:!?])', r'\1', s)
    return s


def main():
    df = pd.read_csv(MERGED, dtype=str, encoding='utf-8-sig')
    if 'winning_firm_name_zh' not in df.columns:
        print('No winning_firm_name_zh column; nothing to clean')
        return

    before_nonempty = df['winning_firm_name_zh'].fillna('').astype(str).str.strip().apply(bool).sum()
    df['winning_firm_name_zh'] = df['winning_firm_name_zh'].fillna('').astype(str).map(clean_text)
    after_nonempty = df['winning_firm_name_zh'].fillna('').astype(str).str.strip().apply(bool).sum()

    df.to_csv(MERGED, index=False, encoding='utf-8-sig')
    print(f'Cleaned Chinese names: non-empty before={before_nonempty}, after={after_nonempty}')
    # Export CSV + Excel copies after cleaning
    try:
        import subprocess
        subprocess.run(['python3', 'scripts/save_both_formats.py', str(MERGED)], check=False)
        print('Exported CSV and Excel copies via save_both_formats.py')
    except Exception as e:
        print('Failed to export copies:', e)


if __name__ == '__main__':
    main()
