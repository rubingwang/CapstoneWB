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

BRICS_COUNTRIES = {
    "Brazil",
    "China",
    "India",
    "Russian Federation",
    "South Africa",
}

REGION_COUNTRY_LABELS = {
    "Andean Countries",
    "Andean Community",
    "Caribbean",
    "Caribbean Region",
    "Central America",
    "Central American Sub-Region",
    "Central American Subregion",
    "Latin America",
    "Latin America and Caribbean",
    "Latin America and the Caribbean",
    "Lac Region",
    "Oecs Countries",
    "OECS Countries",
    "Oecs Sub-Region",
    "Regional",
    "Regional Support",
    "Regional Cooperation",
    "South America",
    "Mercosur",
    "ALBA",
}

MULTI_LAC_LABEL = "99-multiple-lac-country"
INTERNATIONAL_ORG_LABEL = "99-international-organization"


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
        "republic of suriname": "Suriname",
        "republic of haiti": "Haiti",
        "republic of trinidad and tobago": "Trinidad and Tobago",
        "united states of america": "United States",
        "people's republic of china": "China",
        "st. maarten (dutch part)": "St Maarten",
        "sint maarten (dutch part)": "St Maarten",
        "sint maarten": "St Maarten",
        # Saint -> St standardization
        "saint kitts and nevis": "St. Kitts and Nevis",
        "saint lucia": "St. Lucia",
        "saint vincent and the grenadines": "St. Vincent and the Grenadines",
        # Bahamas variations
        "bahamas, the": "Bahamas",
        "bahamas, the ": "Bahamas",
        "bahamas": "Bahamas",
        # Venezuela - normalize to short form
        "venezuela": "Venezuela",
        "venezuela, republica bolivariana de": "Venezuela",
        "venezuela, rb": "Venezuela",
        # Korea
        "korea, republic of": "South Korea",
        "rep. of korea": "South Korea",
        "republic of korea": "South Korea",
        # Iran
        "iran, islamic republic of": "Iran",
        # INTAL -> Latin American Integration Association
        "intal": None,
        # CDB -> not a country
        "cdb": None,
        # Panama Canal Zone -> not a country
        "panama canal zone": None,
        "panama canal zo": None,
        # Stateless/World should be captured as International Organization
        "stateless": INTERNATIONAL_ORG_LABEL,
        "world": INTERNATIONAL_ORG_LABEL,
        "international organization": INTERNATIONAL_ORG_LABEL,
        # Harmonize legacy regional placeholder label
        "multiple-lac-countries": MULTI_LAC_LABEL,
        # Curacao standardization
        "curacao": "Curacao",
        # French Guiana
        "french guiana": "Guiana",
        # World Bank LAC API aliases
        "puerto rico (us)": "Puerto Rico",
        "virgin islands (u.s.)": "United States Virgin Islands",
        "virgin islands (us)": "United States Virgin Islands",
        "st. martin (french part)": "St. Martin",
        "sint maarten (dutch part)": "St Maarten",
        # Other common forms
        "venezuela, republica bolivariana de": "Venezuela",
        "turkiye": "Turkey",
        "slovak republic": "Slovakia",
        "hong kong": "Hong Kong SAR, China",
        "hong kong sar, china": "Hong Kong SAR, China",
        "taiwan, china": "Taiwan",
    }
    return post_fixes.get(normalized.lower(), normalized)


def _split_country_values(value: str | None) -> list[str]:
    if value in (None, ""):
        return []
    return [part.strip() for part in str(value).split(";") if part and part.strip()]


def validate_merged_labels(dataframe: pd.DataFrame) -> None:
    check_columns = ["country", "winning_country", "contractor_country"]
    violations: list[str] = []
    for column in check_columns:
        if column not in dataframe.columns:
            continue

        series = dataframe[column].fillna("").astype(str)
        bad_multi_lac = series.str.contains("Multiple-LAC-Countries", case=False, regex=False)
        bad_int_org = series.str.contains("International Organization", case=False, regex=False)
        if bad_multi_lac.any():
            violations.append(f"{column}: contains legacy label 'Multiple-LAC-Countries'")
        if bad_int_org.any():
            violations.append(f"{column}: contains legacy label 'International Organization'")

        for value in series[series.str.strip() != ""]:
            tokens = _split_country_values(value)
            if any(token in {"World", "Stateless", "world", "stateless"} for token in tokens):
                violations.append(f"{column}: contains raw world/stateless token")
                break

    if violations:
        detail = "\n".join(sorted(set(violations)))
        raise SystemExit(f"Merged label validation failed:\n{detail}")


def normalize_borrower_country(value: str | None) -> str | None:
    normalized = normalize_country_name(value)
    if not normalized:
        return None
    if normalized in REGION_COUNTRY_LABELS:
        return MULTI_LAC_LABEL
    return normalized


def load_country_candidates(wb_df: pd.DataFrame, idb_df: pd.DataFrame, cdb_df: pd.DataFrame) -> list[str]:
    """Build country candidate list from all three raw sources (WB, IDB, CDB)."""
    candidates: list[str] = []
    sources = [
        (wb_df, "borrower_country" if "borrower_country" in wb_df.columns else "country"),
        (idb_df, "operation_country_name"),
        (cdb_df, "country"),
    ]
    for df, col in sources:
        if col not in df.columns:
            continue
        for value in df[col].dropna().astype(str).tolist():
            normalized = normalize_country_name(value)
            if not normalized or normalized in REGION_COUNTRY_LABELS or normalized in GLOBAL_NORTH_COUNTRIES:
                continue
            if normalized not in candidates:
                candidates.append(normalized)
    return sorted(candidates, key=len, reverse=True)


def infer_country_from_project_name(project_name: str | None, candidates: list[str]) -> str | None:
    if not project_name:
        return None
    haystack = normalize_text(project_name)
    if not haystack:
        return None
    lowered = haystack.lower()
    for candidate in candidates:
        needle = candidate.lower()
        if needle and needle in lowered:
            return candidate
    return None


def normalize_project_country(raw_country: str | None, project_name: str | None, candidates: list[str], *, prefer_project_name: bool = False) -> str | None:
    raw_value = normalize_country_name(raw_country)
    inferred_value = infer_country_from_project_name(project_name, candidates)

    if raw_value:
        if prefer_project_name and inferred_value and inferred_value != raw_value:
            return inferred_value
        return raw_value

    if prefer_project_name and inferred_value:
        return inferred_value

    return inferred_value


def normalize_country_cell(value: str | None) -> str | None:
    """Normalize multi-country cell while preserving all original countries."""
    values = split_multi_value(value)
    normalized = [normalize_country_name(item) for item in values]
    normalized = [item for item in normalized if item]
    normalized = dedupe_preserve_order(normalized)
    return "; ".join(normalized) if normalized else None


def parse_countries_with_duplicates(value: str | None) -> list[str]:
    values = split_multi_value(value)
    normalized = [normalize_country_name(item) for item in values]
    return [item for item in normalized if item]


def contractor_country_metrics(winning_country: str | None) -> tuple[int | None, str | None, int | None, str | None]:
    winners = parse_countries_with_duplicates(winning_country)
    if not winners:
        return None, None, None, None

    unique_countries = dedupe_preserve_order(winners)
    if len(unique_countries) <= 1:
        if_joint_venture = "Non-Joint Venture"
    else:
        if_joint_venture = "Joint Venture"

    return (
        len(winners),
        "; ".join(unique_countries),
        len(unique_countries),
        if_joint_venture,
    )


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
    if any(country in BRICS_COUNTRIES for country in normalized):
        return "BRICS"
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
        "winning_firm_numbers",
        "contractor_country",
        "numbers_of_contractor_country",
        "winning_country_type",
        "winning_country_group",
        "if_joint_venture",
        "joint_venture",
    ]


def map_world_bank(wb_df: pd.DataFrame, country_candidates: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in wb_df.iterrows():
        winning_country = normalize_country_cell(row.get("winning_firm_country"))
        project_country = normalize_project_country(
            row.get("borrower_country") if row.get("borrower_country") not in (None, "") else row.get("country"),
            row.get("project_name"),
            country_candidates,
        )
        project_country = normalize_borrower_country(project_country)
        winning_firm_numbers, contractor_country, numbers_of_contractor_country, if_joint_venture = contractor_country_metrics(winning_country)
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
                "country": project_country,
                "contract_value_usd": normalize_float(row.get("contract_value_usd")),
                "winning_country": winning_country,
                "winning_firm_numbers": winning_firm_numbers,
                "contractor_country": contractor_country,
                "numbers_of_contractor_country": numbers_of_contractor_country,
                "winning_country_type": country_type(winning_country),
                "winning_country_group": country_group(winning_country),
                "if_joint_venture": if_joint_venture,
                "joint_venture": if_joint_venture,
            }
        )
    return pd.DataFrame(rows, columns=selected_columns())


def map_idb(idb_df: pd.DataFrame, country_candidates: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in idb_df.iterrows():
        winning_country = normalize_country_name(row.get("awarded_firm_country_name"))
        project_country = normalize_project_country(
            row.get("operation_country_name"),
            row.get("project_name"),
            country_candidates,
        )
        project_country = normalize_borrower_country(project_country)
        winning_firm_numbers, contractor_country, numbers_of_contractor_country, if_joint_venture = contractor_country_metrics(winning_country)
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
                "country": project_country,
                "contract_value_usd": normalize_float(row.get("total_amount")),
                "winning_country": winning_country,
                "winning_firm_numbers": winning_firm_numbers,
                "contractor_country": contractor_country,
                "numbers_of_contractor_country": numbers_of_contractor_country,
                "winning_country_type": country_type(winning_country),
                "winning_country_group": country_group(winning_country),
                "if_joint_venture": if_joint_venture,
                "joint_venture": if_joint_venture,
            }
        )
    return pd.DataFrame(rows, columns=selected_columns())


def map_cdb(cdb_df: pd.DataFrame, country_candidates: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in cdb_df.iterrows():
        winning_country = normalize_country_cell(row.get("winning_country"))
        project_country = normalize_project_country(
            row.get("country"),
            row.get("project_name"),
            country_candidates,
            prefer_project_name=True,
        )
        project_country = normalize_borrower_country(project_country)
        winning_firm_numbers, contractor_country, numbers_of_contractor_country, if_joint_venture = contractor_country_metrics(winning_country)
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
                "country": project_country,
                "contract_value_usd": normalize_float(row.get("contract_value_usd")),
                "winning_country": winning_country,
                "winning_firm_numbers": winning_firm_numbers,
                "contractor_country": contractor_country,
                "numbers_of_contractor_country": numbers_of_contractor_country,
                "winning_country_type": country_type(winning_country),
                "winning_country_group": country_group(winning_country),
                "if_joint_venture": if_joint_venture,
                "joint_venture": if_joint_venture,
            }
        )
    return pd.DataFrame(rows, columns=selected_columns())


def write_outputs(dataframe: pd.DataFrame) -> tuple[Path, Path, Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_frame = dataframe.copy()

    # Keep count fields as nullable integers so CSV does not end up with 1.0/2.0 formatting.
    for column in ("winning_firm_numbers", "numbers_of_contractor_country"):
        if column in csv_frame.columns:
            csv_frame[column] = pd.to_numeric(csv_frame[column], errors="coerce").astype("Int64")

    # Keep blanks as true empty values for better spreadsheet compatibility.
    csv_frame = csv_frame.astype(object).where(pd.notna(csv_frame), "")

    # Excel convention: keep numeric columns numeric so spreadsheet aggregation works.
    excel_frame = csv_frame.copy()
    for column in ("contract_value_usd", "winning_firm_numbers", "numbers_of_contractor_country"):
        if column in excel_frame.columns:
            excel_frame[column] = pd.to_numeric(excel_frame[column], errors="coerce")

    for column in ("winning_firm_numbers", "numbers_of_contractor_country"):
        if column in excel_frame.columns:
            excel_frame[column] = excel_frame[column].astype("Int64")

    dated_suffix = version_suffix()
    dated_csv = OUT_DIR / f"worldbank_idb_cdb_merged_{dated_suffix}.csv"
    dated_xlsx = OUT_DIR / f"worldbank_idb_cdb_merged_{dated_suffix}.xlsx"
    latest_xlsx = OUT_PATH.with_suffix(".xlsx")
    raw_csv = OUT_DIR / "worldbank_idb_cdb_merged_raw.csv"
    raw_xlsx = OUT_DIR / "worldbank_idb_cdb_merged_raw.xlsx"

    # Output merged data (compact/raw 22-column format)
    csv_frame.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    csv_frame.to_csv(dated_csv, index=False, encoding="utf-8-sig")
    csv_frame.to_csv(raw_csv, index=False, encoding="utf-8-sig")
    excel_frame.to_excel(latest_xlsx, index=False)
    excel_frame.to_excel(dated_xlsx, index=False)
    excel_frame.to_excel(raw_xlsx, index=False)
    return OUT_PATH, latest_xlsx, dated_csv, dated_xlsx


def main() -> None:
    wb_df = load_csv(WB_PATH)
    idb_df = load_csv(IDB_PATH)
    cdb_df = load_csv(CDB_PATH)
    country_candidates = load_country_candidates(wb_df, idb_df, cdb_df)

    merged = pd.concat(
        [map_world_bank(wb_df, country_candidates), map_idb(idb_df, country_candidates), map_cdb(cdb_df, country_candidates)],
        ignore_index=True,
        sort=False,
    ).reindex(columns=selected_columns())

    validate_merged_labels(merged)

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