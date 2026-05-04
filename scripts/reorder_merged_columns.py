#!/usr/bin/env python3
"""Reorder merged CSV columns to place winning_firm_name_zh right after winning_firm_name."""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / 'data' / 'worldbank_idb_merged.csv'

df = pd.read_csv(MERGED, dtype=str)

# Define the desired column order
preferred_order = [
    'project_id',
    'notice_type',
    'notice_no',
    'country',
    'year_awarded',
    'date_awarded',
    'data_source',
    'procurement_channel',
    'funding_source',
    'sector',
    'project_type',
    'contract_value_usd',
    'contract_currency',
    'contract_amount',
    'contract_duration_original_unit',
    'contract_duration_original',
    'contract_duration_days',
    'winning_firm_name',
    'winning_firm_name_zh',  # Place Chinese name right after English name
    'winning_firm_code',
    'winning_firm_country',
    'winning_firm_is_chinese',
    'winning_firm_is_soe',
    'number_of_bidders',
    'if_single_bidder',
    'bidder_country_lowest_price',
    'bidder_lowest_price',
    'bidder_country',
    'bidder_price_currency',
    'bidder_price',
    'procurement_method',
    'financing_linked_to_bid',
    'financing_source_chinese',
    'joint_venture',
    'firm_registered_locally',
    'record_id',
    'awarded_date',
    'bid_reference_no',
    'project_name',
    'contract_url',
]

# Keep only columns that exist and preserve order
available = [c for c in preferred_order if c in df.columns]
# Add any remaining columns not in preferred list
remaining = [c for c in df.columns if c not in available]
final_order = available + remaining

# Reorder and save
df = df[final_order]
df.to_csv(MERGED, index=False, encoding='utf-8-sig')
print(f'Reordered columns in {MERGED}')
print(f'Column order: {", ".join(final_order[:10])}... (showing first 10)')
