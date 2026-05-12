#!/usr/bin/env python3
"""Finalize the merged dataset schema and keep backup copies aligned."""

from pathlib import Path
import shutil
import subprocess

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data' / 'worldbank_idb_merged.csv'
BACKUPS = [
    ROOT / 'data' / 'worldbank_idb_merged.backup.csv',
]

DROP_COLUMNS = {
    'contract_amount',
    'contract_duration_original_unit',
    'contract_duration_original',
    'contract_duration_days',
    'funding_source',
    'financing_linked_to_bid',
    'financing_source_chinese',
    'awarded_date',
}

LEADING_ORDER = [
    'year_awarded',
    'date_awarded',
    'notice_type',
    'notice_id',
    'contract_name',
    'project_id',
    'project_name',
    'sector',
    'sector_reclassifcation',
    'project_type',
    'procurement_channel',
]


def load_df(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str).replace({'nan': None})


def finalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if 'notice_no' in df.columns and 'notice_id' not in df.columns:
        df = df.rename(columns={'notice_no': 'notice_id'})
    if 'sector_reclassify' in df.columns and 'sector_reclassifcation' not in df.columns:
        df = df.rename(columns={'sector_reclassify': 'sector_reclassifcation'})
    if 'sector_reclassifcation' not in df.columns:
        df['sector_reclassifcation'] = None

    if 'contract_name' not in df.columns:
        df['contract_name'] = None

    if 'data_source' in df.columns and 'project_name' in df.columns:
        idb_mask = df['data_source'].fillna('').eq('IDB')
        missing_contract_name = df['contract_name'].isna() | df['contract_name'].astype(str).str.strip().eq('')
        fill_mask = idb_mask & missing_contract_name
        df.loc[fill_mask, 'contract_name'] = df.loc[fill_mask, 'project_name']

    df['contract_currency'] = 'USD'

    for col in DROP_COLUMNS:
        if col in df.columns:
            df = df.drop(columns=[col])

    remaining_columns = [col for col in df.columns if col not in LEADING_ORDER]
    final_order = [col for col in LEADING_ORDER if col in df.columns] + remaining_columns
    return df[final_order]


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f'Source file not found: {SOURCE}')

    df = load_df(SOURCE)
    finalized = finalize_df(df)
    finalized.to_csv(SOURCE, index=False, encoding='utf-8-sig')
    print(f'Updated {SOURCE} ({len(finalized)} rows, {len(finalized.columns)} columns)')

    for target in BACKUPS:
        if target.exists():
            shutil.copy2(SOURCE, target)
            print(f'Copied {SOURCE.name} -> {target.name}')

    subprocess.run(['python3', 'scripts/save_both_formats.py', str(SOURCE)], check=False)
    print('Exported CSV and Excel copies via save_both_formats.py')


if __name__ == '__main__':
    main()
