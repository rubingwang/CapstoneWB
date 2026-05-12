# CapstoneWB

## Overview

CapstoneWB is a procurement dataset combining **World Bank** and **Inter-American Development Bank (IDB)** contract records for Latin America and the Caribbean (LAC) with Chinese company participation. The dataset includes **145 verified contracts** and has been cleaned, standardized, and enriched with sector reclassification and firm country information.

- **Total Records**: 145 contracts
- **World Bank**: 60 records (2001-2025)
- **Inter-American Development Bank**: 85 records (2010-2025)
- **Last Updated**: May 2026
- **Coverage**: All historical procurement records available (截止到 2026 年 5 月)

## Live Site

For a quick view of the dataset without downloading files, open the browser viewer here:

- [CapstoneWB Data Viewer](https://rubingwang.github.io/CapstoneWB/)

## Dataset Structure

| Field | Description |
|-------|-------------|
| `year_awarded` | Award year for filtering and analysis |
| `date_awarded` | Full award date (YYYY-MM-DD format) |
| `notice_type` | Contract (standardized to "Contract" for all records) |
| `notice_id` | Unique contract identifier |
| `contract_name` | Contract title / procurement description |
| `project_id` | Funding project identifier |
| `project_name` | Project name from source metadata |
| `sector` | Standardized 8-category sector classification |
| `project_type` | Procurement type (e.g., Works, Goods, Services) |
| `procurement_channel` | Procurement method label |
| `data_source` | Source: "World Bank" or "Inter-American Development Bank" |
| `country` | Project country (standardized format with title case) |
| `contract_value_usd` | Contract value in USD |
| `contract_currency` | Normalized to USD |
| `winning_firm_name` | Awarded contractor name |
| `winning_firm_name_zh` | Contractor name in Chinese (when available) |
| `winning_firm_code` | Contractor code/ID from source data |
| `winning_firm_country` | Contractor country |
| `winning_firm_is_chinese` | Flag: 1 if Chinese firm, 0 if not |
| `winning_firm_is_soe` | Flag: 1 if state-owned enterprise (inferred) |
| `joint_venture` | Flag: 1 if joint venture, 0 if not |
| `contract_url` | Direct URL to contract record |
| `record_id` | Internal record identifier |
| `bid_reference_no` | Bid reference number |

## Sector Classification

All 145 records are classified into 8 standardized sectors based on contract name and procurement details:

- **Infrastructure & Energy**: 76 records (electrification, power transmission, water systems)
- **Health**: 33 records (vaccines, medical equipment, health programs)
- **Education**: 10 records (school construction, educational equipment)
- **Water, Sanitation & Waste**: 10 records
- **Industry, Trade & Finance**: 10 records
- **Agriculture**: 2 records
- **Digital Economy & ICT**: 2 records
- **Public Admin & Governance**: 2 records

## Data Quality Notes

- **Missing Values**: Represented as "." (single dot placeholder)
- **Country Names**: Standardized to Title Case with lowercase conjunctions (e.g., "Trinidad and Tobago")
- **Data Sources**: "Inter-American Development Bank" (standardized from "IDB")
- **URLs**: All records include valid contract URLs
  - World Bank: Direct project contract links
  - IDB: Official IDB procurement dashboard
- **Contract Names**: IDB records with missing titles fall back to project names

## Project Layout

- `src/capstonewb/`: Python package (CLI entry point, data models, config)
- `data/worldbank_idb_merged.csv`: Primary merged dataset (145 records, 24 columns)
- `data/worldbank_idb_merged.backup.csv`: Synchronized backup copy
- `data/worldbank_idb_merged.xlsx`: Excel export of merged dataset
- `docs/data/worldbank_idb_merged.csv`: Copy for web viewer
- `docs/data/worldbank_idb_merged.xlsx`: Excel copy for web viewer
- `docs/index.html`: Browser-based data viewer

## Setup & Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -e .
```

## Data Access

### CSV Format
Primary dataset available in three synchronized copies:
- `data/worldbank_idb_merged.csv` (main source)
- `data/worldbank_idb_merged.backup.csv` (backup)

All use UTF-8-sig encoding for Excel compatibility.

### Excel Format
- `data/worldbank_idb_merged.xlsx`
- `docs/data/worldbank_idb_merged.xlsx` (for web viewer)

### Web Viewer
Open `docs/index.html` or visit the GitHub Pages deployment to explore records interactively without downloading files.

The web viewer supports:
- Filtering by year, country, and data source
- Keyword search across contract names and firm names
- Pagination and data export
- Interactive sorting and viewing

## Data Processing Notes

### Schema Evolution
This dataset has undergone careful standardization:
- **Column Count**: 24 fields (removed: contract_amount, durations, financing fields)
- **Sector Reclassification**: Keywords from contract names analyzed to assign 8-category sectors
- **Data Source Standardization**: "Inter-American Development Bank" (previously "IDB")
- **Country Standardization**: Title Case with lowercase conjunctions
- **Missing Value Handling**: All NULL/empty cells replaced with "." placeholder

### Data Verification
- All 145 records verified for accuracy
- Contract URLs tested for validity
- Chinese firm names reviewed and standardized
- Duplicate records merged where applicable
- Sector classifications validated against procurement descriptions

## Version Information

- **Dataset Version**: May 2026
- **Record Count**: 145 (60 World Bank + 85 IDB)
- **Last Verified**: May 12, 2026
- **Coverage Period**: 2001-2026
