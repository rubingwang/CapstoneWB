#!/usr/bin/env python3
"""Import extra Excel datasets from data/ folders, convert to CSV, and merge into WB-aligned merged CSV.

Usage: run from repo root: `python3 scripts/import_and_merge_extras.py`

Behavior:
- Looks for Excel files in `data/aiddata/` and `data/caribbean_development_bank/`.
- Converts any .xlsx/.xls to CSV (same folder).
- Attempts a conservative mapping: if sheet columns contain IDB-like fields (e.g. `total_amount`, `awarded_firm_name`), maps using IDB->WB mapping and appends to `data/worldbank_idb_merged.csv`.
- If mapping cannot be determined, it will drop a CSV and print instructions for manual mapping.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_DIRS = [ROOT / 'data' / 'aiddata', ROOT / 'data' / 'caribbean_development_bank']
MERGED_PATH = ROOT / 'data' / 'worldbank_idb_aiddata_cdb_merged.csv'


def excel_to_csv(xpath, out_csv):
    df = pd.read_excel(xpath, dtype=str)
    df = df.replace({np.nan: None})
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print('Wrote CSV:', out_csv)
    return out_csv


def map_idb_like(df, wb_cols):
    # reuse mapping from scripts/merge_worldbank_idb.py
    m = {
        'project_id': 'project_number',
        'notice_no': 'contract_id',
        'country': 'operation_country_name',
        'year_awarded': 'contract_year',
        'date_awarded': 'signature_date',
        'data_source': None,
        'procurement_channel': 'procurement_type',
        'funding_source': 'source',
        'sector': 'economic_sector_name',
        'project_type': 'operation_type_name',
        'contract_value_usd': 'total_amount',
        'contract_amount': 'idb_amount',
        'winning_firm_name': 'awarded_firm_name',
        'winning_firm_country': 'awarded_firm_country_name',
        'winning_firm_code': 'awarded_firm_country_code',
        'project_name': 'project_name',
        'contract_url': None,
    }
    rows = []
    for _, r in df.iterrows():
        out = {c: None for c in wb_cols}
        for wb_col, src_col in m.items():
            if src_col and src_col in df.columns:
                out[wb_col] = r.get(src_col)
        out['data_source'] = 'EXTRA'
        rows.append(out)
    return pd.DataFrame(rows, columns=wb_cols)


def main():
    if not MERGED_PATH.exists():
        print('Merged file not found at', MERGED_PATH)
        sys.exit(1)

    merged_df = pd.read_csv(MERGED_PATH, dtype=str).replace({np.nan: None})
    wb_cols = list(merged_df.columns)

    appended = []
    for d in DATA_DIRS:
        if not d.exists():
            print('Skipping missing directory', d)
            continue
        # find excel files
        excels = list(d.glob('*.xlsx')) + list(d.glob('*.xls'))
        if not excels:
            print('No Excel files in', d)
            continue
        for x in excels:
            csv_out = d / (x.stem + '.csv')
            excel_to_csv(x, csv_out)
            df = pd.read_csv(csv_out, dtype=str).replace({np.nan: None})
            # decide if IDB-like
            idb_likes = {'total_amount', 'awarded_firm_name', 'project_number'}
            if idb_likes.intersection(set(df.columns)):
                print('Detected IDB-like columns in', csv_out.name, '; mapping and appending')
                mapped = map_idb_like(df, wb_cols)
                appended.append(mapped)
            else:
                print('Could not automatically map columns for', csv_out.name)
                print('Columns:', list(df.columns)[:10])
                print('Please open', csv_out, 'and adapt mapping if needed.')

    if appended:
        new = pd.concat(appended, ignore_index=True, sort=False)
        result = pd.concat([merged_df, new], ignore_index=True, sort=False)
        result.to_csv(MERGED_PATH, index=False, encoding='utf-8-sig')
        print('Appended', len(new), 'rows and updated merged file at', MERGED_PATH)
        # Export CSV + Excel copies
        try:
            import subprocess
            subprocess.run(['python3', 'scripts/save_both_formats.py', str(MERGED_PATH)], check=False)
            print('Exported CSV and Excel copies via save_both_formats.py')
        except Exception as e:
            print('Failed to export copies:', e)
    else:
        print('No rows appended. Nothing changed.')


if __name__ == '__main__':
    main()
