# CapstoneWB

## Overview

CapstoneWB is a procurement data pipeline for Latin America and the Caribbean (LAC).
It integrates records from three multilateral development banks:

- World Bank (WB)
- Inter-American Development Bank (IDB)
- Caribbean Development Bank (CDB)

The project provides reproducible scripts to generate raw datasets, merge them into a common schema, and export final dated analysis files.

## Current Outputs

Main merged artifacts:

- `data/merged_data/worldbank_idb_cdb_merged_raw.csv`
- `data/merged_data/worldbank_idb_cdb_merged_raw.xlsx`
- `data/merged_data/worldbank_idb_cdb_merged_0614.csv`
- `data/merged_data/worldbank_idb_cdb_merged_0614.xlsx`

World Bank raw artifacts:

- `data/raw/world_bank/world_bank_lac_raw.csv`
- `data/raw/world_bank/world_bank_lac_raw.xlsx`
- `data/raw/world_bank/world_bank_lac_raw.metadata.json`

Current finalized dataset snapshot:

- File: `data/merged_data/worldbank_idb_cdb_merged_0614.csv`
- Rows: `237651`
- Columns: `19`

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

### 3) Merge WB + IDB + CDB into raw merged table

```bash
python3 scripts/merge_worldbank_idb_cdb_compact.py
```

### 4) Build finalized dated output

```bash
python3 scripts/reformat_worldbank_idb_cdb_merged_raw.py
```

## Final Dataset Schema (0614)

The finalized 0614 file contains the following columns:

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
16. `number_of_contractor_country`
17. `contractor_country_type`
18. `contractor_country_group`
19. `if_joint_venture`

## Key Definitions

- `borrower country`: borrowing country (or standardized LAC regional label where applicable)
- `contractor_country`: normalized winning contractor country field
- `number_of_contractor`: number of winning contractors
- `number_of_contractor_country`: number of unique contractor countries
- `if_joint_venture`: joint-venture status derived from contractor-country structure
- `contractor_country_type`: country-type classification used for analysis
- `contractor_country_group`: global south or global north grouping

## Country Standardization (Current 0614)

- Borrower-country names are standardized to consistent labels in the finalized output.
- Common abbreviated country names are normalized to full forms (for example, `St. Lucia` -> `Saint Lucia`).
- `St Maarten` is standardized as `Sint Maarten`.
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
