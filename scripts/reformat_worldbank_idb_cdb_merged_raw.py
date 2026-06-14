#!/usr/bin/env python3
"""Create a dated, renamed, reordered merged dataset from the immutable raw merge."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "merged_data" / "worldbank_idb_cdb_merged_raw.csv"
OUTPUT_DIR = ROOT / "data" / "merged_data"


OUTPUT_COLUMNS = [
    "year_awarded",
    "date_awarded",
    "borrower country",
    "notice_id",
    "contract_name",
    "contract_url",
    "project_id",
    "project_name",
    "project_type",
    "project_sector",
    "procurement_channel",
    "data_source",
    "contract_value_usd",
    "number_of_contractor",
    "contractor_country",
    "number_of_contractor_country",
    "contractor_country_type",
    "contractor_country_group",
    "if_joint_venture",
]


NUMERIC_COLUMNS = [
    "contract_value_usd",
    "number_of_contractor",
    "number_of_contractor_country",
]


RENAMES = {
    "country": "borrower country",
    "project_url": "contract_url",
    "winning_firm_numbers": "number_of_contractor",
    "numbers_of_contractor_country": "number_of_contractor_country",
    "winning_country_type": "contractor_country_type",
    "winning_country_group": "contractor_country_group",
}


SECTOR_RULES: list[tuple[str, str]] = [
    (
        "Education and Human Capital",
        (
            "education",
            "school",
            "teacher",
            "student",
            "early childhood",
            "learning",
            "skills",
            "training",
            "human capital",
            "employability",
            "vocational",
        ),
    ),
    (
        "Health and Social Protection",
        (
            "health",
            "medical",
            "hospital",
            "clinic",
            "primary health",
            "health care",
            "public health",
            "social protection",
            "poverty",
            "safety net",
            "citizen safety",
            "nutrition",
            "ambulance",
        ),
    ),
    (
        "Infrastructure and Transport",
        (
            "transport",
            "highway",
            "road",
            "bridge",
            "port",
            "airport",
            "infrastructure",
            "urban",
            "housing",
            "neighborhood",
            "mobility",
            "transit",
            "logistics",
            "construction",
            "reconstruction",
            "resilience",
            "city",
            "urban",
        ),
    ),
    (
        "Water, Sanitation and Waste Management",
        (
            "water",
            "sanitation",
            "wastewater",
            "sewer",
            "waste",
            "drainage",
            "water supply",
            "water and sanitation",
            "wastewater",
        ),
    ),
    (
        "Agriculture and Food Security",
        (
            "agric",
            "agriculture",
            "agribusiness",
            "food security",
            "food safety",
            "irrigation",
            "livestock",
            "farming",
            "farm",
            "rural",
            "productive",
        ),
    ),
    (
        "Energy, Climate and Environment",
        (
            "energy",
            "electric",
            "power",
            "transmission",
            "extractive",
            "climate",
            "environment",
            "ecosystem",
            "biodiversity",
            "disaster",
            "forest",
            "conservation",
            "renewable",
            "carbon",
            "redd",
            "blue economy",
        ),
    ),
    (
        "Public Administration and Governance",
        (
            "reform",
            "public sector",
            "governance",
            "justice",
            "modernization",
            "decentralization",
            "administration",
            "fiscal policy",
            "state support",
            "institution",
            "cadaster",
            "land administration",
            "governing",
            "public investment",
            "public finance",
            "data",
            "identif",
            "policy",
            "management",
            "competitiveness",
            "innovation",
            "enterprise",
            "business",
            "sme",
            "microenterprise",
            "market",
            "trade",
            "tourism",
            "ict",
            "digital",
            "financial",
            "finance",
        ),
    ),
]


def version_suffix() -> str:
    return datetime.now().strftime("%m%d")


def load_raw() -> pd.DataFrame:
    if not SOURCE.exists():
        raise SystemExit(f"Source file not found: {SOURCE}")
    return pd.read_csv(SOURCE, dtype=str).replace({"nan": None})


def classify_sector(project_name: str | None, contract_name: str | None) -> str | None:
    return classify_sector_from_text(project_name, contract_name)


def classify_sector_from_text(project_name: str | None, contract_name: str | None) -> str | None:
    text = " ".join(
        part.strip()
        for part in [str(project_name or ""), str(contract_name or "")]
        if part and str(part).strip()
    ).lower()
    if not text:
        return None

    for label, keywords in SECTOR_RULES:
        if any(keyword in text for keyword in keywords):
            return label
    return "Public Administration and Governance"


def classify_sector_from_source_sector(source_sector: str | None) -> str | None:
    text = str(source_sector or "").strip().lower()
    if not text:
        return None

    raw_rules: list[tuple[str, tuple[str, ...]]] = [
        (
            "Education and Human Capital",
            ("education", "school", "human capital", "training", "skills", "early childhood", "vocational"),
        ),
        (
            "Health and Social Protection",
            ("health", "social protection", "poverty", "nutrition", "citizen safety", "safety"),
        ),
        (
            "Infrastructure and Transport",
            ("transport", "infrastructure", "housing", "urban", "road", "highway", "neighborhood", "logistics"),
        ),
        (
            "Water, Sanitation and Waste Management",
            ("water", "sanit", "waste", "sewer", "drainage"),
        ),
        (
            "Agriculture and Food Security",
            ("agriculture", "agribusiness", "food", "rural", "irrigation", "livestock", "farm"),
        ),
        (
            "Energy, Climate and Environment",
            ("energy", "extractives", "climate", "environment", "biodiversity", "disaster", "forest", "conservation", "ecosystem", "redd"),
        ),
        (
            "Public Administration and Governance",
            ("public admin", "governance", "reform", "justice", "decentralization", "fiscal", "institution", "policy", "management", "financial", "private", "trade", "industry", "ict", "information", "communication", "tourism", "sme", "microenterprise", "innovation", "compet"),
        ),
    ]

    for label, keywords in raw_rules:
        if any(keyword in text for keyword in keywords):
            return label
    return "Public Administration and Governance"


def transform(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    raw_sector = frame.get("sector")

    for old_name, new_name in RENAMES.items():
        if old_name in frame.columns:
            frame = frame.rename(columns={old_name: new_name})

    project_sector_values = []
    project_names = frame.get("project_name")
    contract_names = frame.get("contract_name")
    if project_names is None:
        project_names = [None] * len(frame)
    if contract_names is None:
        contract_names = [None] * len(frame)
    if raw_sector is None:
        raw_sector = [None] * len(frame)

    for project_name, contract_name, source_sector in zip(project_names, contract_names, raw_sector):
        classified = classify_sector_from_text(project_name, contract_name)
        fallback = classify_sector_from_source_sector(source_sector)
        if classified == "Public Administration and Governance" and fallback:
            classified = fallback
        project_sector_values.append(classified)

    frame["project_sector"] = project_sector_values

    # Keep the base file intact and generate a new analysis-friendly version.
    for column in OUTPUT_COLUMNS:
        if column not in frame.columns:
            frame[column] = None

    ordered = frame[OUTPUT_COLUMNS].copy()
    ordered = ordered.astype(object).where(pd.notna(ordered), "")
    ordered = ordered.apply(lambda column: column.map(lambda value: "" if isinstance(value, str) and not value.strip() else value))
    return ordered


def write_outputs(frame: pd.DataFrame) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dated_suffix = version_suffix()
    csv_path = OUTPUT_DIR / f"worldbank_idb_cdb_merged_{dated_suffix}.csv"
    xlsx_path = OUTPUT_DIR / f"worldbank_idb_cdb_merged_{dated_suffix}.xlsx"

    frame.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Keep blanks in CSV, but write true numeric cells to Excel
    # so users can calculate directly in spreadsheet tools.
    excel_frame = frame.copy()
    for col in NUMERIC_COLUMNS:
        if col in excel_frame.columns:
            excel_frame[col] = pd.to_numeric(
                excel_frame[col], errors="coerce"
            )
    excel_frame.to_excel(xlsx_path, index=False)
    return csv_path, xlsx_path


def main() -> None:
    raw = load_raw()
    transformed = transform(raw)
    csv_path, xlsx_path = write_outputs(transformed)
    print(
        {
            "source": str(SOURCE),
            "rows": int(len(transformed)),
            "columns": list(transformed.columns),
            "output_csv": str(csv_path),
            "output_xlsx": str(xlsx_path),
        }
    )


if __name__ == "__main__":
    main()