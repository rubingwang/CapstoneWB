#!/usr/bin/env python3
"""Generate a World Bank LAC non-Chinese contract dataset.

This script pulls World Bank contract records for Latin America and the Caribbean,
filters out suppliers whose country is explicitly China, and writes a CSV/XLSX pair plus a small
metadata summary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from capstonewb.world_bank import fetch_world_bank_contracts


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "worldbank"
OUTPUT_BASENAME = "world_bank_lac_non_chinese_20260522_v2"
OUTPUT_CSV = OUTPUT_DIR / f"{OUTPUT_BASENAME}.csv"
OUTPUT_XLSX = OUTPUT_DIR / f"{OUTPUT_BASENAME}.xlsx"
OUTPUT_META = OUTPUT_DIR / f"{OUTPUT_BASENAME}.metadata.json"


def is_china_country(row: pd.Series) -> bool:
    country = str(row.get("winning_firm_country") or "").strip().upper()
    return country == "CHINA"


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

    df = pd.DataFrame([record.to_dict() for record in records])
    if df.empty:
        raise SystemExit("No World Bank records were returned.")

    non_chinese = df.loc[~df.apply(is_china_country, axis=1)].copy()
    non_chinese = non_chinese.fillna("")

    # Keep the contract value field intact; only normalize to numeric when possible.
    if "contract_value_usd" in non_chinese.columns:
        non_chinese["contract_value_usd"] = pd.to_numeric(non_chinese["contract_value_usd"], errors="coerce")

    non_chinese.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    non_chinese.to_excel(OUTPUT_XLSX, index=False, engine="openpyxl")

    summary = {
        "source": "World Bank",
        "region": "Latin America and Caribbean",
        "start_year": 2015,
        "end_year": 2026,
        "total_records": int(len(df)),
        "non_chinese_records": int(len(non_chinese)),
        "unique_projects": int(non_chinese["project_id"].fillna("").nunique()) if "project_id" in non_chinese.columns else 0,
        "removed_china_records": int(len(df) - len(non_chinese)),
        "non_chinese_contract_value_usd_sum": float(non_chinese["contract_value_usd"].fillna(0).sum()) if "contract_value_usd" in non_chinese.columns else 0.0,
        "output_csv": str(OUTPUT_CSV),
        "output_xlsx": str(OUTPUT_XLSX),
    }
    OUTPUT_META.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()