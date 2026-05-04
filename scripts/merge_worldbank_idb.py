#!/usr/bin/env python3
"""Merge World Bank and IDB datasets aligning to World Bank columns.

Outputs: data/worldbank_idb_merged.csv
"""
import pandas as pd
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WB_PATH = ROOT / 'data' / 'worldbank' / 'world_bank_lac_contracts_china_60.csv'
IDB_PATH = ROOT / 'data' / 'idb' / 'IDB_Project_Procurement_Awards_Dataset.csv'
OUT_PATH = ROOT / 'data' / 'worldbank_idb_merged.csv'


def load_csv(path):
    return pd.read_csv(path, dtype=str).replace({np.nan: None})


def normalize_date(s):
    if pd.isna(s) or s is None:
        return None
    s = str(s).strip()
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return pd.to_datetime(s, dayfirst=False).strftime('%Y-%m-%d')
        except Exception:
            continue
    # fallback: let pandas try
    try:
        return pd.to_datetime(s).strftime('%Y-%m-%d')
    except Exception:
        return s


def map_idb_to_wb(idb_df, wb_cols):
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
        # Use IDB's `total_amount` as the WB `contract_value_usd` per user request
        'contract_value_usd': 'total_amount',
        'contract_amount': 'idb_amount',
        'winning_firm_name': 'awarded_firm_name',
        'winning_firm_country': 'awarded_firm_country_name',
        'winning_firm_code': 'awarded_firm_country_code',
        'project_name': 'project_name',
        'contract_url': None,
    }

    rows = []
    for _, r in idb_df.iterrows():
        out = {c: None for c in wb_cols}
        for wb_col, idb_col in m.items():
            if idb_col and idb_col in idb_df.columns:
                out[wb_col] = r.get(idb_col)
        # derived / fixed fields
        out['data_source'] = 'IDB'
        # normalize dates
        if 'date_awarded' in out and out['date_awarded']:
            out['date_awarded'] = normalize_date(out['date_awarded'])
        # winning_firm_is_chinese: check country name or code
        wfcn = (out.get('winning_firm_country') or '')
        wfcode = (out.get('winning_firm_code') or '')
        if 'winning_firm_is_chinese' in wb_cols:
            is_china = False
            if isinstance(wfcn, str) and 'CHINA' in wfcn.upper():
                is_china = True
            if isinstance(wfcode, str) and wfcode.upper() in ('CHN', 'CN', 'CHINA'):
                is_china = True
            out['winning_firm_is_chinese'] = 'True' if is_china else 'False'
        rows.append(out)

    return pd.DataFrame(rows, columns=wb_cols)


def main():
    wb_df = load_csv(WB_PATH)
    idb_df = load_csv(IDB_PATH)

    wb_cols = list(wb_df.columns)

    idb_mapped = map_idb_to_wb(idb_df, wb_cols)

    # ensure columns types consistent
    merged = pd.concat([wb_df, idb_mapped], ignore_index=True, sort=False)

    # write with utf-8-sig for proper Unicode support in Excel
    merged.to_csv(OUT_PATH, index=False, encoding='utf-8-sig')
    print('Wrote merged dataset to', OUT_PATH)


if __name__ == '__main__':
    main()
