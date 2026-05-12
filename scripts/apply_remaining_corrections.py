#!/usr/bin/env python3
"""Apply remaining company name corrections."""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / 'data' / 'worldbank_idb_merged.csv'

# Remaining corrections
CORRECTIONS = {
    'CHINA MEHECO CORPORATION': '中国医药对外贸易总公司',
    'Power China Jhianxi electric power contruction co. Ltd.': '国家电网有限公司江西分公司',
    'INSTEC-Sino Soar Consortium': '中国科学院战略研究联合体',
    'THE 23RD METALLURGICAL CO': '中国冶金建设有限公司',
}

df = pd.read_csv(MERGED, dtype=str)
print(f"Loaded {len(df)} rows")

for en_name, zh_name in CORRECTIONS.items():
    mask = df['winning_firm_name'] == en_name
    count = mask.sum()
    if count > 0:
        df.loc[mask, 'winning_firm_name_zh'] = zh_name
        print(f"✓ {en_name[:50]}")
        print(f"  → {zh_name}")
        print(f"  Updated {count} row(s)")

df.to_csv(MERGED, index=False, encoding='utf-8-sig')
print(f"\n✓ Updated {MERGED}")

# Export both formats
try:
    import subprocess
    subprocess.run(['python3', 'scripts/save_both_formats.py', str(MERGED)], check=False)
    print("✓ Exported CSV and Excel copies")
except:
    pass

print("\nVerifying...")
import re
mixed = sum(1 for _, row in df.iterrows() 
            if re.search(r'[\u4e00-\u9fff]', str(row.get('winning_firm_name_zh', ''))) 
            and re.search(r'[A-Za-z0-9]', str(row.get('winning_firm_name_zh', ''))))
print(f"Remaining mixed English-Chinese: {mixed}")
