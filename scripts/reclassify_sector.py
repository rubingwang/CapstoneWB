#!/usr/bin/env python3
"""Reclassify project sectors into seven higher-level groups."""

from __future__ import annotations

import re
import subprocess

import pandas as pd


CATEGORY_LABELS = {
    "infra": "Infrastructure & Energy",
    "water": "Water, Sanitation & Waste",
    "education": "Education",
    "health": "Health",
    "industry": "Industry, Trade & Finance",
    "agri": "Agriculture",
    "digital": "Digital Economy & ICT",
    "public": "Public Admin & Governance",
}


PATTERN_RULES = [
    (
        "water",
        [
            r"water supply",
            r"water and sanitation",
            r"sanitation",
            r"sewerage",
            r"sewage",
            r"wastewater",
            r"solid waste",
            r"waste management",
            r"irrigation",
            r"drainage",
            r"water/sanit/waste",
        ],
    ),
    (
        "education",
        [
            r"education",
            r"school",
            r"university",
            r"vocational",
            r"training",
            r"textbook",
            r"human capital",
        ],
    ),
    (
        "health",
        [
            r"hospital",
            r"clinic",
            r"medical equipment",
            r"health care",
            r"public health",
            r"health",
            r"vaccine",
            r"vaccination",
            r"covid",
            r"health system",
            r"maternal",
            r"child development",
        ],
    ),
    (
        "digital",
        [
            r"digital",
            r"information technology",
            r"ict",
            r"e-government",
            r"software",
            r"connectivity",
            r"broadband",
            r"cyber",
            r"telecom",
            r"information and communication",
            r"data center",
        ],
    ),
    (
        "industry",
        [
            r"export promotion",
            r"investment promotion",
            r"investment",
            r"competitiveness",
            r"trade",
            r"banking",
            r"financial",
            r"msme",
            r"private sector",
            r"customs",
            r"tax",
            r"fiscal",
            r"business climate",
            r"innovation",
            r"competitiveness and trade",
            r"agribusiness",
        ],
    ),
    (
        "agri",
        [
            r"crop",
            r"agricultur",
            r"livestock",
            r"forestry",
            r"fisher",
            r"food security",
            r"rural development",
            r"agribusiness",
            r"blue economy",
            r"fisheries sector",
            r"rural road",
        ],
    ),
    (
        "public",
        [
            r"law",
            r"justice",
            r"institutional",
            r"governance",
            r"reform",
            r"public sector",
            r"public admin",
            r"legal",
            r"capacity building",
            r"public expenditure",
            r"public policy",
            r"institutional strengthening",
            r"emergency recovery",
            r"recovery project",
            r"disaster",
            r"security strengthening",
            r"citizen safety",
        ],
    ),
    (
        "infra",
        [
            r"road",
            r"highway",
            r"bridge",
            r"railway",
            r"transport",
            r"rail",
            r"metro",
            r"port",
            r"airport",
            r"infrastructure",
            r"power",
            r"electricity",
            r"energy",
            r"renewable",
            r"hydropower",
            r"hydroelectric",
            r"hydro",
            r"solar",
            r"wind",
            r"transmission",
            r"distribution grid",
            r"grid",
            r"electrification",
            r"powerhouse",
            r"utility",
            r"energy efficiency",
            r"extractives",
            r"urban development",
            r"urban rehabilitation",
            r"urban infrastructure",
            r"road infrastructure",
        ],
    ),
]


SECTOR_FALLBACK_RULES = [
    ("water", [r"water", r"sanit", r"waste"]),
    ("education", [r"education", r"school", r"university"]),
    ("health", [r"health", r"hospital", r"clinic", r"medical", r"vaccine"]),
    ("digital", [r"info & communication", r"information", r"digital", r"ict"]),
    ("industry", [r"business climate", r"competitiveness", r"export", r"investment", r"fiscal", r"industry & trade"]),
    ("agri", [r"agriculture", r"rural", r"crop", r"livestock", r"fisher"]),
    ("public", [r"public admin", r"reform", r"public sector", r"institutional", r"justice", r"legal"]),
    ("infra", [r"transport", r"energy", r"extractives", r"urban", r"major highways", r"power", r"electricity", r"road", r"railway"]),
]


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def classify_sector(row: pd.Series) -> str:
    project_name = normalize_text(row.get("project_name"))
    sector = normalize_text(row.get("sector"))
    text = f"{project_name} {sector}".strip()

    if "rural" in text and any(keyword in text for keyword in ["agricultur", "fisher", "forestry", "livestock", "food security", "agribusiness", "blue economy"]):
        return CATEGORY_LABELS["agri"]

    for category_key, patterns in PATTERN_RULES:
        for pattern in patterns:
            if re.search(pattern, text):
                return CATEGORY_LABELS[category_key]

    for category_key, patterns in SECTOR_FALLBACK_RULES:
        for pattern in patterns:
            if re.search(pattern, sector):
                return CATEGORY_LABELS[category_key]

    return ""


def main() -> None:
    input_path = "data/worldbank_idb_aiddata_cdb_merged.csv"
    df = pd.read_csv(input_path, dtype=str)

    df["sector_reclassify"] = df.apply(classify_sector, axis=1)

    if "sector" in df.columns and "sector_reclassify" in df.columns:
        columns = df.columns.tolist()
        columns.remove("sector_reclassify")
        insert_at = columns.index("sector") + 1
        columns.insert(insert_at, "sector_reclassify")
        df = df[columns]

    df.to_csv(input_path, index=False, encoding="utf-8-sig")

    counts = df["sector_reclassify"].replace("", pd.NA).value_counts(dropna=False)
    print("sector_reclassify counts:")
    print(counts)
    print(f"\nSaved: {input_path}")

    subprocess.run(["python3", "scripts/save_both_formats.py"], check=True)


if __name__ == "__main__":
    main()