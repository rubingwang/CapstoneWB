#!/usr/bin/env python3
"""Generate the raw World Bank LAC procurement contract dataset.

This script pulls all World Bank project procurement contracts for
Latin America and the Caribbean and writes them to a source-separated
raw CSV using the existing World Bank field order.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from capstonewb.world_bank import fetch_world_bank_contracts


OUTPUT_DIR = ROOT / "data" / "raw" / "world_bank"
OUTPUT_BASENAME = "world_bank_lac_raw"
OUTPUT_CSV = OUTPUT_DIR / f"{OUTPUT_BASENAME}.csv"
OUTPUT_META = OUTPUT_DIR / f"{OUTPUT_BASENAME}.metadata.json"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    records = fetch_world_bank_contracts(
        start_year=2015,
        end_year=2026,
        rows=500,
        limit=None,
        region_name="Latin America and Caribbean",
        contractor_country=None,
    )

    dataframe = pd.DataFrame([record.to_dict() for record in records])
    if dataframe.empty:
        raise SystemExit("No World Bank records were returned.")

    dataframe = dataframe.fillna("")
    dataframe.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    summary = {
        "source": "World Bank",
        "region": "Latin America and Caribbean",
        "start_year": 2015,
        "end_year": 2026,
        "total_records": int(len(dataframe)),
        "output_csv": str(OUTPUT_CSV),
        "columns": list(dataframe.columns),
    }
    OUTPUT_META.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()