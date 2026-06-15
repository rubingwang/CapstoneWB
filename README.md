# CapstoneWB

## Overview

CapstoneWB is a procurement contract data pipeline for Latin America and the Caribbean (LAC).
It currently integrates three multilateral development bank sources: World Bank, IDB, and CDB.
The project goal is to provide a reproducible workflow for data generation, standardization, merge, and export for downstream analysis and thesis work.

The statistics below are based on `data/merged_data/worldbank_idb_cdb_merged_0615.csv`.

Baseline coverage:

- Start date: `2000-07-01`
- End date: `2026-06-09`
- Total contracts: `237,651`

Per data source:

- World Bank
  - Contracts: `78,950`
  - Borrower countries (`borrower country`, distinct): `33`
  - Cumulative contract value (USD): `41,392,362,556.55`
- IDB
  - Contracts: `158,272`
  - Borrower countries (`borrower country`, distinct): `27`
  - Cumulative contract value (USD): `59,490,595,185.55`
- CDB
  - Contracts: `429`
  - Borrower countries (`borrower country`, distinct): `20`
  - Cumulative contract value (USD): `1,154,888,051.84`

Grand total:

- Total contracts: `237,651`
- Borrower countries (`borrower country`, distinct): `39`
- Cumulative contract value (USD): `102,037,845,793.94`

## Key definition

Field definitions for the current finalized dataset (0615):

1. `year_awarded`: Contract award year.
2. `date_awarded`: Contract award date (typically YYYY-MM-DD).
3. `borrower country`: Borrowing country / project implementation country.
4. `notice_id`: Procurement notice or contract record identifier.
5. `contract_name`: Contract title (procurement package title).
6. `contract_url`: Link to the contract or project procurement record.
7. `project_id`: Project identifier.
8. `project_name`: Project title.
9. `project_type`: Procurement category (for example, goods, works, consulting).
10. `project_sector`: Project sector (mapped into standardized sector groups).
11. `procurement_channel`: Procurement channel.
12. `data_source`: Source institution (World Bank / IDB / CDB).
13. `contract_value_usd`: Contract amount in USD.
14. `number_of_contractor`: Number of awarded contractors.
15. `contractor_country`: Original contractor-country field (can be multi-valued).
16. `contractor_country_unique`: Unique contractor-country field. Rule: default to the first country; if `Hong Kong SAR, China` appears, use it; otherwise, if `China/中国` appears, use `China`.
17. `number_of_contractor_country`: Number of contractor countries.
18. `contractor_country_type`: Contractor-country type grouping.
19. `contractor_country_group`: Contractor-country bloc grouping (for example, G7/BRICS/Others).
20. `if_joint_venture`: Joint-venture flag.

## Pipeline

### 1) Environment setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### 2) Regenerate World Bank raw data

```bash
python3 scripts/generate_worldbank_raw.py
```

### 3) Regenerate CDB raw data (includes parser/FX validation)

```bash
python3 scripts/generate_cdb_raw.py
```

### 4) Merge WB + IDB + CDB into raw merged table

```bash
python3 scripts/merge_worldbank_idb_cdb_compact.py
```

### 5) Build finalized dated output

```bash
python3 scripts/reformat_worldbank_idb_cdb_merged_raw.py
```

## Final Dataset Schema (0615)

The finalized 0615 file contains the following columns:

1. `year_awarded`
2. `date_awarded`
3. `borrower country`
4. `notice_id`
5. `contract_name`
6. `contract_url`
7. `project_id`
8. `project_name`
9. `project_type`
10. `project_sector`
11. `procurement_channel`
12. `data_source`
13. `contract_value_usd`
14. `number_of_contractor`
15. `contractor_country`
16. `contractor_country_unique`
17. `number_of_contractor_country`
18. `contractor_country_type`
19. `contractor_country_group`
20. `if_joint_venture`

## Country Standardization (Current 0615)

- Borrower-country names are standardized to consistent labels in the finalized output.
- Regional borrower placeholders are normalized as `99-multiple-lac-country`.
- `World` / `Stateless` placeholders are normalized as `99-international-organization`.
- Common abbreviated country names are normalized to full forms (for example, `St. Lucia` -> `Saint Lucia`).
- `St Maarten` is standardized as `Sint Maarten`.
- `Hong Kong` is standardized as `Hong Kong SAR, China`.
- Contractor-country values are standardized to a consistent country-name format for cross-source analysis.

## Sector Taxonomy

The current final classification uses seven sector groups:

- Infrastructure and Transport
- Energy, Climate and Environment
- Education and Human Capital
- Health and Social Protection
- Agriculture and Food Security
- Public Administration and Governance
- Water, Sanitation and Waste Management

## Amount and Currency

- World Bank rows use `contract_value_usd` from WB raw contract output.
- IDB rows use `total_amount` as the merge amount source.
- CDB rows are converted to USD during raw generation and stored as `contract_value_usd`.

## Repository Layout

- `src/capstonewb/`: package code (CLI, source-specific crawlers, models)
- `scripts/`: generation and merge scripts
- `data/raw/`: source-level raw datasets
- `data/merged_data/`: merged and finalized exports
- `docs/`: static viewer assets and data dictionary
