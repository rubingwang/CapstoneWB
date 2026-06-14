#!/usr/bin/env python3
"""Generate the raw Caribbean Development Bank contract awards dataset.

The CDB contract awards page exposes a YEAR filter and paginated tables.
This script crawls every available year, parses the Winning Bid field into
country, firm, currency, and amount, and writes a source-separated raw CSV.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from capstonewb.cdb import fetch_cdb_contract_awards, save_records


BASE_URL = "https://www.caribank.org/work-with-us/procurement/contract-awards"
DEFAULT_OUTPUT_CSV = ROOT / "data" / "raw" / "cdb" / "cdb_lac_raw.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="generate_cdb_raw.py")
    parser.add_argument("--start-year", type=int, default=2012)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of records to write")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_CSV))
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = output_path.with_suffix(".metadata.json")

    years = list(range(args.start_year, args.end_year + 1))
    records = fetch_cdb_contract_awards(years=years)
    if args.limit is not None:
        records = records[: args.limit]
    if not records:
        raise SystemExit("No CDB records were returned.")

    save_records(records, str(output_path))

    # Guardrail: if currency is parsed but USD is still missing, stop the pipeline.
    df = pd.read_csv(output_path, dtype=str, keep_default_na=False)
    currency = df.get("currency_unit", pd.Series([""] * len(df))).astype(str).str.strip()
    usd = df.get("contract_value_usd", pd.Series([""] * len(df))).astype(str).str.strip()
    missing_usd = usd.eq("") | usd.eq(".") | usd.str.lower().eq("nan")
    has_currency = currency.ne("")
    unresolved = int((missing_usd & has_currency).sum())
    if unresolved > 0:
        raise SystemExit(
            f"CDB raw validation failed: {unresolved} rows have currency_unit but missing contract_value_usd. "
            "Regenerate after fixing parser/FX mapping before merging."
        )

    dataframe_columns = list(records[0].to_dict().keys())
    summary = {
        "source": "CDB",
        "region": "Latin America and the Caribbean",
        "start_year": args.start_year,
        "end_year": args.end_year,
        "total_records": int(len(records)),
        "output_csv": str(output_path),
        "columns": dataframe_columns,
    }
    metadata_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()