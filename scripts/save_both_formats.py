#!/usr/bin/env python3
"""Save CSV in UTF-8-SIG and write Excel (.xlsx) copy to avoid Chinese garbling.

Usage:
  python3 scripts/save_both_formats.py path/to/file.csv

If no path given, defaults to data/worldbank_idb_merged.csv
Also copies the outputs to docs/data/ with same filenames.
"""
import sys
from pathlib import Path
import pandas as pd


def save_both(csv_path: Path):
    csv_path = csv_path.resolve()
    if not csv_path.exists():
        raise SystemExit(f'CSV not found: {csv_path}')

    df = pd.read_csv(csv_path, dtype=str)

    # write CSV with BOM for Excel compatibility
    csv_path.write_text(df.to_csv(index=False, encoding='utf-8-sig'), encoding='utf-8-sig')

    # write Excel (xlsx) using openpyxl
    xlsx_path = csv_path.with_suffix('.xlsx')
    df.to_excel(xlsx_path, index=False, engine='openpyxl')

    # copy to docs/data
    docs_dir = csv_path.parents[1] / 'docs' / 'data' if (csv_path.parents[1] / 'docs').exists() else Path('docs') / 'data'
    docs_dir.mkdir(parents=True, exist_ok=True)
    docs_csv = docs_dir / csv_path.name
    docs_xlsx = docs_dir / xlsx_path.name
    docs_csv.write_bytes(csv_path.read_bytes())
    docs_xlsx.write_bytes(xlsx_path.read_bytes())

    print('Wrote:', csv_path)
    print('Wrote:', xlsx_path)
    print('Copied to docs:', docs_csv, docs_xlsx)


def main():
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('data/worldbank_idb_merged.csv')
    save_both(p)


if __name__ == '__main__':
    main()
