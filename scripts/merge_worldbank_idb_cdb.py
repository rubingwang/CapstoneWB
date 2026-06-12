#!/usr/bin/env python3
"""Merge World Bank, IDB, and CDB procurement datasets into a WB-shaped CSV."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WB_PATH = ROOT / "data" / "raw" / "world_bank" / "world_bank_lac_raw.csv"
IDB_PATH = ROOT / "data" / "raw" / "idb" / "IDB_Project_Procurement_Awards_Dataset0612.csv"
CDB_PATH = ROOT / "data" / "raw" / "cdb" / "cdb_lac_raw.csv"
OUT_DIR = ROOT / "data" / "merged_data"
OUT_PATH = OUT_DIR / "worldbank_idb_cdb_merged.csv"


def load_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path, dtype=str)
    return dataframe.where(pd.notna(dataframe), None)


def normalize_date(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for _fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return pd.to_datetime(text).strftime("%Y-%m-%d")
        except Exception:
            continue
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


def is_china_country(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    text = str(value).strip().lower()
    if "china" in text or text in {"chn", "cn", "prc", "people's republic of china", "people republic of china"}:
        return 1
    return 0


def same_country(left: str | None, right: str | None) -> int | None:
    if left in (None, "") or right in (None, ""):
        return None
    return 1 if normalize_text(left).lower() == normalize_text(right).lower() else 0


def wb_columns() -> list[str]:
    return list(load_csv(WB_PATH).columns)


def map_idb_to_wb(idb_df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in idb_df.iterrows():
        output = {column: None for column in columns}
        output.update(
            {
                "project_id": row.get("project_number"),
                "notice_type": "Contract Award",
                "notice_no": row.get("contract_id"),
                "country": row.get("operation_country_name"),
                "year_awarded": normalize_int(row.get("contract_year")),
                "date_awarded": normalize_date(row.get("signature_date")),
                "data_source": "IDB",
                "procurement_channel": row.get("procurement_type"),
                "funding_source": row.get("source"),
                "sector": row.get("economic_sector_name"),
                "project_type": row.get("operation_type_name"),
                "contract_value_usd": normalize_float(row.get("total_amount")),
                "contract_currency": None,
                "contract_amount": None,
                "winning_firm_name": row.get("awarded_firm_name"),
                "winning_firm_code": row.get("awarded_firm_country_code"),
                "winning_firm_country": row.get("awarded_firm_country_name"),
                "winning_firm_is_chinese": is_china_country(row.get("awarded_firm_country_name")) or is_china_country(row.get("awarded_firm_country_code")),
                "winning_firm_is_soe": None,
                "number_of_bidders": None,
                "if_single_bidder": None,
                "bidder_country_lowest_price": None,
                "bidder_lowest_price": None,
                "bidder_country": None,
                "bidder_price_currency": None,
                "bidder_price": None,
                "procurement_method": row.get("procurement_type"),
                "financing_linked_to_bid": None,
                "financing_source_chinese": None,
                "joint_venture": None,
                "firm_registered_locally": same_country(row.get("awarded_firm_country_name"), row.get("operation_country_name")),
                "record_id": row.get("contract_id"),
                "awarded_date": normalize_date(row.get("signature_date")),
                "bid_reference_no": None,
                "project_name": row.get("project_name"),
                "contract_url": None,
            }
        )
        rows.append(output)
    return pd.DataFrame(rows, columns=columns)


def map_cdb_to_wb(cdb_df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in cdb_df.iterrows():
        output = {column: None for column in columns}
        output.update(
            {
                "project_id": None,
                "notice_type": "Contract Award",
                "notice_no": row.get("notice_id"),
                "country": row.get("country"),
                "year_awarded": normalize_int(row.get("award_year")),
                "date_awarded": None,
                "data_source": "CDB",
                "procurement_channel": row.get("procurement_type"),
                "funding_source": None,
                "sector": row.get("sector"),
                "project_type": row.get("procurement_type"),
                "contract_value_usd": normalize_float(row.get("contract_value_usd")),
                "contract_currency": row.get("currency_unit"),
                "contract_amount": normalize_float(row.get("contract_amount")),
                "winning_firm_name": row.get("winning_firm"),
                "winning_firm_code": None,
                "winning_firm_country": row.get("winning_country"),
                "winning_firm_is_chinese": is_china_country(row.get("winning_country")),
                "winning_firm_is_soe": None,
                "number_of_bidders": None,
                "if_single_bidder": None,
                "bidder_country_lowest_price": None,
                "bidder_lowest_price": None,
                "bidder_country": None,
                "bidder_price_currency": None,
                "bidder_price": None,
                "procurement_method": row.get("procurement_type"),
                "financing_linked_to_bid": None,
                "financing_source_chinese": None,
                "joint_venture": None,
                "firm_registered_locally": same_country(row.get("winning_country"), row.get("country")),
                "record_id": row.get("notice_id"),
                "awarded_date": None,
                "bid_reference_no": None,
                "project_name": row.get("project_name"),
                "contract_url": row.get("notice_url"),
            }
        )
        rows.append(output)
    return pd.DataFrame(rows, columns=columns)


def clean_output_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUT_DIR.iterdir():
        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)


def main() -> None:
    columns = wb_columns()
    wb_df = load_csv(WB_PATH).reindex(columns=columns)
    idb_df = load_csv(IDB_PATH)
    cdb_df = load_csv(CDB_PATH)

    merged = pd.concat(
        [wb_df, map_idb_to_wb(idb_df, columns), map_cdb_to_wb(cdb_df, columns)],
        ignore_index=True,
        sort=False,
    ).reindex(columns=columns)

    clean_output_dir()
    merged.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    summary = {
        "output_csv": str(OUT_PATH),
        "rows": int(len(merged)),
        "wb_rows": int(len(wb_df)),
        "idb_rows": int(len(idb_df)),
        "cdb_rows": int(len(cdb_df)),
        "columns": list(merged.columns),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()