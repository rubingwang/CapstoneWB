# CapstoneWB

## Summary

CapstoneWB is a Python scraping pipeline for World Bank procurement notices, focused on Latin America and the Caribbean (LAC). It pulls notice data from the official World Bank procurement API, enriches records with conservative text parsing from notice detail content, and exports thesis-ready CSV datasets.

Current workflow supports:

- Notice-level extraction (one row per notice, no project dedup)
- Yearly exports (for example, 2015-2025: one CSV per year)
- A merged export that combines all yearly files into one dataset
- Conservative null-first logic: when a field is not reliably present, leave it blank instead of guessing

## Data Scope

- Region: Latin America and the Caribbean (LAC)
- Source APIs:
	- World Bank Procurement Notices API (`search.worldbank.org/api/v2/procnotices`)
	- World Bank Country Metadata API
- Typical period: 2015-2025 (configurable by CLI arguments)

## Project Layout

- `src/capstonewb/cli.py`: command line entry point
- `src/capstonewb/world_bank.py`: fetching, detail merging, parsing, transformation
- `src/capstonewb/models.py`: output schema (`ProcurementRecord`)
- `src/capstonewb/config.py`: constants and defaults
- `data/`: generated CSV files

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Core Logic (How The Pipeline Works)

1. Fetch notices by API pages (`rows` + offset).
2. Build LAC scope via country metadata and query procurement notices.
3. Optionally keep all notice types (`--all-notice-types`) or apply notice-type filters.
4. Merge list response with notice detail content when available.
5. Parse winner/bidder and date blocks from notice text.
6. Apply conservative inference helpers (for example, local registration, Chinese firm flag).
7. Emit CSV in UTF-8 with BOM (`utf-8-sig`) for spreadsheet compatibility.

Important design choices:

- Keep unknown values as blank/`NULL`.
- Parsing is best-effort and conservative; no aggressive imputation.
- Notice-level mode (`--notice-level`) preserves all notices instead of one row per project.

## Output Variables (Full Dictionary)

All columns come from `ProcurementRecord`.

- `project_id`: World Bank project identifier linked to the notice.
- `notice_type`: Notice category (for example, `Contract Award`, `General Procurement Notice`).
- `notice_no`: Notice ID used as notice number (mapped from API `id`).
- `country`: Project country.
- `year_awarded`: Award year used for filtering and analysis.
- `date_awarded`: Full award notification date parsed from `Date Notification of Award Issued` (`YYYY/MM/DD` when available).
- `data_source`: Data origin label (currently `World Bank`).
- `procurement_channel`: Procurement channel label (currently MDB-financed channel label).
- `funding_source`: Funding identifiers extracted from API credit/financing blocks.
- `sector`: Sector value extracted from notice metadata.
- `project_type`: Inferred project type from procurement grouping metadata.
- `contract_value_usd`: Contract value in USD when a reliable USD value exists; otherwise blank.
- `contract_currency`: Original contract currency parsed from notice.
- `contract_amount`: Original contract amount parsed from notice.
- `contract_duration_original_unit`: Duration unit in source text (`Day(s)`, `Week(s)`, `Month(s)`, `Year(s)` when present).
- `contract_duration_original`: Numeric duration in original unit.
- `contract_duration_days`: Duration normalized to days.
- `winning_firm_name`: Parsed awarded winner name.
- `winning_firm_code`: Winner code parsed from winner name block (for example, bracketed numeric code).
- `winning_firm_country`: Parsed winner country.
- `winning_firm_is_chinese`: Winner-country-based flag: China=1, non-China=0, unknown country=blank.
- `winning_firm_is_soe`: Best-effort inferred SOE indicator from available text cues; blank if unavailable.
- `number_of_bidders`: Parsed/derived bidder count.
- `if_single_bidder`: Single-bid indicator (1 if single bidder condition is met, else 0/blank based on available data).
- `bidder_country_lowest_price`: Bidder country associated with lowest parsed bidder price.
- `bidder_lowest_price`: Lowest parsed bidder price.
- `bidder_country`: Parsed bidder country list/value from notice text.
- `bidder_price_currency`: Currency for parsed bidder prices.
- `bidder_price`: Parsed bidder price list/value.
- `procurement_method`: Procurement method from notice metadata.
- `financing_linked_to_bid`: Best-effort indicator whether financing appears linked to bidding terms.
- `financing_source_chinese`: Best-effort indicator of Chinese financing source.
- `joint_venture`: Parsed/inferred joint-venture indicator.
- `firm_registered_locally`: Three-state field: local=1, known non-local=0, unknown=blank.
- `record_id`: Internal record ID (API notice `id`).
- `awarded_date`: Backward-compatible alias of award date (same value as `date_awarded`).
- `bid_reference_no`: Bid reference number from source metadata.
- `project_name`: Project name from source metadata.
- `contract_url`: World Bank procurement detail URL for this notice.

## Practical Notes On Missing Values

- Some old years have sparse detail content (`notice_text` missing or incomplete).
- Winner/bidder fields can be blank when the source notice has no structured awarded block.
- This is expected behavior by design and not treated as an automatic parsing failure.

## Run Commands

### Single Output (Custom Window)

```bash
capstonewb scrape-world-bank \
	--start-year 2024 \
	--end-year 2024 \
	--all-notice-types \
	--notice-level \
	--rows 500 \
	--output data/world_bank_lac_2024_notice_level.csv
```

### Yearly Files + Merged File (2015-2025)

```bash
outdir=data/world_bank_lac_2015_2025_yearly_notice_level
mkdir -p "$outdir"

for y in $(seq 2015 2025); do
	capstonewb scrape-world-bank \
		--start-year "$y" \
		--end-year "$y" \
		--all-notice-types \
		--notice-level \
		--rows 500 \
		--output "$outdir/world_bank_lac_${y}_notice_level.csv"
done
```

Merge yearly files:

```bash
python - <<'PY'
import glob
import os
import pandas as pd

outdir = 'data/world_bank_lac_2015_2025_yearly_notice_level'
files = sorted(glob.glob(os.path.join(outdir, 'world_bank_lac_*_notice_level.csv')))
merged = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
merged.to_csv(
		os.path.join(outdir, 'world_bank_lac_2015_2025_notice_level_merged.csv'),
		index=False,
		encoding='utf-8-sig',
)
print('merged rows:', len(merged))
PY
```

## Current Output Location (2015-2025)

- Folder: `data/world_bank_lac_2015_2025_yearly_notice_level`
- Yearly files: `world_bank_lac_2015_notice_level.csv` ... `world_bank_lac_2025_notice_level.csv`
- Merged file: `world_bank_lac_2015_2025_notice_level_merged.csv`
