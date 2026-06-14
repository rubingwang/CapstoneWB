# CapstoneWB

## Overview

CapstoneWB is a procurement data pipeline that combines three MDB sources:

- World Bank (WB)
- Inter-American Development Bank (IDB)
- Caribbean Development Bank (CDB)

The current pipeline produces a merged dataset focused on Latin America and the Caribbean (LAC), with standardized country names and contractor-country metrics for joint-venture analysis.

## Current Status (June 2026)

Latest merged run summary:

- Total rows: 237,651
- WB rows: 78,950
- IDB rows: 158,272
- CDB rows: 429
- Output columns: 22

Primary output files:

- `data/merged_data/worldbank_idb_cdb_merged.csv`
- `data/merged_data/worldbank_idb_cdb_merged.xlsx`
- `data/merged_data/worldbank_idb_cdb_merged_0613.csv`
- `data/merged_data/worldbank_idb_cdb_merged_0613.xlsx`

## Current Data Construction Logic

### 1) WB crawler redesign (contract-level + project-level join)

WB extraction now uses contract records as the base (one row per contract), then enriches each contract with project-level metadata.

- Contract endpoint provides contractor fields (for winning firm and winning firm country)
- Project detail endpoint provides borrower country and implementing agency
- Project detail fetch is cached and batched by unique project_id to reduce repeated requests

Key effect:

- `borrower_country` and `winning_firm_country` are now separated correctly
- `implementing_agency` is populated from project detail where available

### 2) Merge logic and standardization

Merge logic in `scripts/merge_worldbank_idb_cdb_compact.py` now includes:

- WB aggregate borrower labels mapped to `Multiple-LAC-Countries`
  - examples remapped: `Andean Countries`, `Caribbean`, `Central America`, `Latin America and Caribbean`, `OECS Countries`
- country-name standardization updates (common forms)
  - examples: `Bahamas, The -> Bahamas`, `Venezuela, Republica Bolivariana de -> Venezuela`, `Turkiye -> Turkey`
- new contractor-country metrics:
  - `winning_firm_numbers`
  - `contractor_country`
  - `numbers_of_contractor_country`
  - `if_joint_venture`
- joint venture classification now follows contractor-country count:
  - `numbers_of_contractor_country = 1 -> Non-Joint Venture`
  - `numbers_of_contractor_country > 1 -> Joint Venture`

### 3) Numeric formatting in merged output

The count fields are exported as integer-like values (for example `1`, `2`, `3`) instead of float-like text (`1.0`, `2.0`).

## Merged Schema (Current)

Current merged columns:

1. `year_awarded`
2. `date_awarded`
3. `notice_id`
4. `contract_name`
5. `project_id`
6. `project_name`
7. `sector`
8. `project_type`
9. `project_url`
10. `procurement_channel`
11. `data_source`
12. `bid_reference_no`
13. `country`
14. `contract_value_usd`
15. `winning_country`
16. `winning_firm_numbers`
17. `contractor_country`
18. `numbers_of_contractor_country`
19. `winning_country_type`
20. `winning_country_group`
21. `if_joint_venture`
22. `joint_venture`

## Key Field Definitions

- `winning_country`: normalized winning contractor country cell (semicolon-delimited when multiple)
- `winning_firm_numbers`: number of winning-firm country entries before country de-duplication
- `contractor_country`: de-duplicated winning countries joined by semicolon
- `numbers_of_contractor_country`: number of unique contractor countries in `contractor_country`
- `if_joint_venture`: JV classification based on `numbers_of_contractor_country`
- `country`: project/borrower country after normalization; WB aggregate region-like labels are set to `Multiple-LAC-Countries`

## Repository Layout

- `src/capstonewb/`: core package (models, WB crawler, CLI)
- `scripts/generate_worldbank_raw.py`: build WB raw contract dataset
- `scripts/merge_worldbank_idb_cdb_compact.py`: merge WB + IDB + CDB into compact schema
- `data/raw/world_bank/`: WB raw outputs
- `data/raw/idb/`: IDB raw inputs
- `data/raw/cdb/`: CDB raw inputs
- `data/merged_data/`: merged CSV/XLSX outputs
- `docs/`: browser viewer assets

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Run Pipeline

### 1) Regenerate WB raw contracts

```bash
python3 scripts/generate_worldbank_raw.py
```

Outputs:

- `data/raw/world_bank/world_bank_lac_raw.csv`
- `data/raw/world_bank/world_bank_lac_raw.xlsx`
- `data/raw/world_bank/world_bank_lac_raw.metadata.json`

### 2) Merge WB + IDB + CDB

```bash
python3 scripts/merge_worldbank_idb_cdb_compact.py
```

Outputs:

- `data/merged_data/worldbank_idb_cdb_merged.csv`
- `data/merged_data/worldbank_idb_cdb_merged.xlsx`
- dated versions with `MMDD` suffix

## Final Version Notes

This README documents the current final dataset version and pipeline outputs only.

- WB aggregate borrower labels are normalized to `Multiple-LAC-Countries`
- Contractor-country metrics are available for JV analysis
- `if_joint_venture` is derived from `numbers_of_contractor_country`
- Country naming variants are standardized through mapping rules
