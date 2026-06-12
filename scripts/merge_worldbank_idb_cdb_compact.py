#!/usr/bin/env python3
"""Merge World Bank, IDB, and CDB procurement data into a compact WB-shaped CSV."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WB_PATH = ROOT / "data" / "raw" / "world_bank" / "world_bank_lac_raw.csv"
IDB_PATH = ROOT / "data" / "raw" / "idb" / "IDB_Project_Procurement_Awards_Dataset0612.csv"
CDB_PATH = ROOT / "data" / "raw" / "cdb" / "cdb_lac_raw.csv"
OUT_DIR = ROOT / "data" / "merged_data"
OUT_PATH = OUT_DIR / "worldbank_idb_cdb_merged.csv"


def version_suffix() -> str:
    return datetime.now().strftime("%m%d")


COUNTRY_STOPWORDS = {
    "and",
    "of",
    "the",
    "de",
    "del",
    "da",
    "do",
    "di",
    "la",
    "le",
    "los",
    "las",
    "y",
    "&",
}

GLOBAL_NORTH_COUNTRIES = {
    "Australia",
    "Austria",
    "Belgium",
    "Canada",
    "Denmark",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Iceland",
    "Ireland",
    "Israel",
    "Italy",
    "Japan",
    "Luxembourg",
    "Netherlands",
    "New Zealand",
    "Norway",
    "Portugal",
    "Singapore",
    "South Korea",
    "Spain",
    "Sweden",
    "Switzerland",
    "United Kingdom",
    "United States",
}

G7_COUNTRIES = {
    "Canada",
    "France",
    "Germany",
    "Italy",
    "Japan",
    "United Kingdom",
    "United States",
}

BRICKES_COUNTRIES = {
    "Brazil",
    "China",
    "India",
    "Russian Federation",
    "South Africa",
}


def load_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path, dtype=str)
    return dataframe.where(pd.notna(dataframe), None)


def normalize_date(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        return pd.to_datetime(text).strftime("%Y-%m-%d")
    except Exception:
        return text or None


def normalize_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def normalize_text(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    text = " ".join(str(value).split()).strip()
    return text or None


def split_multi_value(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def title_case_token(token: str) -> str:
    if not token:
        return token
    if token.isupper() and len(token) <= 4:
        return token
    if token.lower() in COUNTRY_STOPWORDS:
        return token.lower()
    parts = token.split("'")
    return "'".join(part[:1].upper() + part[1:].lower() if part else part for part in parts)


def normalize_country_name(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    text = normalize_text(str(value))
    if not text:
        return None

    lowered = text.lower()
    prefix_replacements = [
        ("people's republic of ", ""),
        ("plurinational state of ", ""),
        ("estado plurinacional de ", ""),
        ("republic of ", ""),
        ("republica de ", ""),
        ("republica bolivariana de ", ""),
        ("democratic republic of ", ""),
        ("federal republic of ", ""),
        ("islamic republic of ", ""),
        ("kingdom of ", ""),
        ("state of ", ""),
        ("the ", ""),
    ]
    for prefix, replacement in prefix_replacements:
        if lowered.startswith(prefix):
            lowered = replacement + lowered[len(prefix):]
            break

    tokens = re.split(r"(\s+)", lowered)
    normalized_tokens: list[str] = []
    for token in tokens:
        if not token or token.isspace():
            normalized_tokens.append(token)
            continue
        normalized_tokens.append(title_case_token(token))

    normalized = "".join(normalized_tokens).strip()
    normalized = normalized.replace("  ", " ")

    post_fixes = {
        "Republic Of Suriname": "Suriname",
        "Republic Of Haiti": "Haiti",
        "Republic Of Trinidad And Tobago": "Trinidad and Tobago",
        "United States Of America": "United States",
        "People'S Republic Of China": "China",
        "St. Maarten (Dutch Part)": "St Maarten",
        "Sint Maarten (Dutch Part)": "St Maarten",
    }
    return post_fixes.get(normalized, normalized)


def normalize_country_cell(value: str | None) -> str | None:
    values = split_multi_value(value)
    normalized = [normalize_country_name(item) for item in values]
    normalized = [item for item in normalized if item]
    normalized = dedupe_preserve_order(normalized)
    return "; ".join(normalized) if normalized else None


def country_type(value: str | None) -> str | None:
    countries = split_multi_value(value)
    normalized = [normalize_country_name(item) for item in countries]
    normalized = [item for item in normalized if item]
    if not normalized:
        return None
    return "The Global North" if all(country in GLOBAL_NORTH_COUNTRIES for country in normalized) else "The Global South"


def country_group(value: str | None) -> str | None:
    countries = split_multi_value(value)
    normalized = [normalize_country_name(item) for item in countries]
    normalized = [item for item in normalized if item]
    if not normalized:
        return None
    if any(country in G7_COUNTRIES for country in normalized):
        return "G7"
    if any(country in BRICKES_COUNTRIES for country in normalized):
        return "BRICKES"
    return "Others"


def joint_venture_label(name: str | None, country: str | None, flag: str | None) -> str | None:
    flag_value = str(flag).strip().lower() if flag not in (None, "") else ""
    if flag_value in {"1", "true", "yes", "y", "joint venture"}:
        return "Joint Venture"
    if len([item for item in split_multi_value(country) if item.strip()]) > 1:
        return "Joint Venture"
    text = f"{name or ''} {country or ''}".lower()
    if "joint venture" in text or "consortium" in text or "consorcio" in text:
        return "Joint Venture"
    return "Non Joint Venture"


def selected_columns() -> list[str]:
    return [
        "year_awarded",
        "date_awarded",
        "notice_id",
        "contract_name",
        "project_id",
        "project_name",
        "sector",
        "project_type",
        "project_url",
        "procurement_channel",
        "data_source",
        "bid_reference_no",
        "country",
        "contract_value_usd",
        "winning_country",
        "winning_country_type",
        "winning_country_group",
        "joint_venture",
    ]


def map_world_bank(wb_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in wb_df.iterrows():
        winning_country = normalize_country_cell(row.get("winning_firm_country"))
        contract_name = normalize_text(row.get("project_name"))
        rows.append(
            {
                "year_awarded": normalize_int(row.get("year_awarded")),
                "date_awarded": normalize_date(row.get("date_awarded") or row.get("awarded_date")),
                "notice_id": row.get("notice_no"),
                "contract_name": contract_name,
                "project_id": row.get("project_id"),
                "project_name": row.get("project_name"),
                "sector": row.get("sector"),
                "project_type": row.get("project_type"),
                "project_url": row.get("contract_url"),
                "procurement_channel": row.get("procurement_channel"),
                "data_source": row.get("data_source") or "World Bank",
                "bid_reference_no": row.get("bid_reference_no"),
                "country": normalize_country_name(row.get("country")),
                "contract_value_usd": normalize_float(row.get("contract_value_usd")),
                "winning_country": winning_country,
                "winning_country_type": country_type(winning_country),
                "winning_country_group": country_group(winning_country),
                "joint_venture": joint_venture_label(row.get("winning_firm_name"), winning_country, row.get("joint_venture")),
            }
        )
    return pd.DataFrame(rows, columns=selected_columns())


def map_idb(idb_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in idb_df.iterrows():
        winning_country = normalize_country_name(row.get("awarded_firm_country_name"))
        rows.append(
            {
                "year_awarded": normalize_int(row.get("contract_year")),
                "date_awarded": normalize_date(row.get("signature_date")),
                "notice_id": row.get("contract_id"),
                "contract_name": normalize_text(row.get("project_name")),
                "project_id": row.get("project_number"),
                "project_name": row.get("project_name"),
                "sector": row.get("economic_sector_name"),
                "project_type": row.get("operation_type_name"),
                "project_url": None,
                "procurement_channel": row.get("procurement_type"),
                "data_source": "IDB",
                "bid_reference_no": None,
                "country": normalize_country_name(row.get("operation_country_name")),
                "contract_value_usd": normalize_float(row.get("total_amount")),
                "winning_country": winning_country,
                "winning_country_type": country_type(winning_country),
                "winning_country_group": country_group(winning_country),
                "joint_venture": joint_venture_label(row.get("awarded_firm_name"), winning_country, None),
            }
        )
    return pd.DataFrame(rows, columns=selected_columns())


def map_cdb(cdb_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in cdb_df.iterrows():
        winning_country = normalize_country_cell(row.get("winning_country"))
        rows.append(
            {
                "year_awarded": normalize_int(row.get("award_year")),
                "date_awarded": None,
                "notice_id": row.get("notice_id"),
                "contract_name": normalize_text(row.get("project_name")),
                "project_id": None,
                "project_name": row.get("project_name"),
                "sector": row.get("sector"),
                "project_type": row.get("procurement_type"),
                "project_url": row.get("notice_url"),
                "procurement_channel": row.get("procurement_type"),
                "data_source": "CDB",
                "bid_reference_no": None,
                "country": normalize_country_name(row.get("country")),
                "contract_value_usd": normalize_float(row.get("contract_value_usd")),
                "winning_country": winning_country,
                "winning_country_type": country_type(winning_country),
                "winning_country_group": country_group(winning_country),
                "joint_venture": joint_venture_label(row.get("winning_firm"), winning_country, None),
            }
        )
    return pd.DataFrame(rows, columns=selected_columns())


def write_outputs(dataframe: pd.DataFrame) -> tuple[Path, Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dated_suffix = version_suffix()
    dated_csv = OUT_DIR / f"worldbank_idb_cdb_merged_{dated_suffix}.csv"
    dated_xlsx = OUT_DIR / f"worldbank_idb_cdb_merged_{dated_suffix}.xlsx"
    latest_xlsx = OUT_PATH.with_suffix(".xlsx")

    dataframe.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    dataframe.to_csv(dated_csv, index=False, encoding="utf-8-sig")
    dataframe.to_excel(latest_xlsx, index=False)
    dataframe.to_excel(dated_xlsx, index=False)
    return OUT_PATH, latest_xlsx, dated_csv, dated_xlsx


def main() -> None:
    wb_df = load_csv(WB_PATH)
    idb_df = load_csv(IDB_PATH)
    cdb_df = load_csv(CDB_PATH)

    merged = pd.concat(
        [map_world_bank(wb_df), map_idb(idb_df), map_cdb(cdb_df)],
        ignore_index=True,
        sort=False,
    ).reindex(columns=selected_columns())

    latest_csv, latest_xlsx, dated_csv, dated_xlsx = write_outputs(merged)

    summary = {
        "output_csv": str(latest_csv),
        "output_xlsx": str(latest_xlsx),
        "versioned_csv": str(dated_csv),
        "versioned_xlsx": str(dated_xlsx),
        "rows": int(len(merged)),
        "wb_rows": int(len(wb_df)),
        "idb_rows": int(len(idb_df)),
        "cdb_rows": int(len(cdb_df)),
        "columns": list(merged.columns),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()