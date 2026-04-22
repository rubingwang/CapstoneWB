"""World Bank procurement scraping helpers."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any, Iterable
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from .config import DEFAULT_ROWS_PER_PAGE, WORLD_BANK_COUNTRY_API, WORLD_BANK_NOTICES_API
from .models import ProcurementRecord


_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X) CapstoneWB/0.1"
_DETAIL_WORKERS = 8
_PROCUREMENT_DETAIL_BASE_URL = "https://projects.worldbank.org/en/projects-operations/procurement-detail"


def _json_get(url: str) -> Any:
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def _json_get_with_retry(url: str, attempts: int = 3, delay_seconds: float = 1.0) -> Any:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return _json_get(url)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(delay_seconds * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError("Failed to fetch JSON payload")


def _fetch_notice_detail(notice_id: str) -> dict[str, Any]:
    params = {
        "format": "json",
        "apilang": "en",
        "fl": "*",
        "id": notice_id,
    }
    url = f"{WORLD_BANK_NOTICES_API}?{urlencode(params)}"
    try:
        payload = _json_get_with_retry(url)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return {}
    notices = payload.get("procnotices", [])
    if not notices:
        return {}
    return notices[0]


def _merge_notice_with_detail(notice: dict[str, Any]) -> dict[str, Any]:
    notice_id = notice.get("id")
    detail = _fetch_notice_detail(notice_id) if notice_id else {}
    return {**notice, **detail}


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def _parse_award_year(notice: dict[str, Any]) -> int | None:
    text_candidates = [notice.get("noticedate"), notice.get("submission_date"), notice.get("notice_text")]
    for candidate in text_candidates:
        if not candidate:
            continue
        if isinstance(candidate, str):
            match = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", candidate)
            if match:
                return int(match.group(1))
            match = re.search(r"\b(20\d{2})\b", candidate)
            if match:
                return int(match.group(1))
            try:
                return datetime.strptime(candidate[:11], "%d-%b-%Y").year
            except ValueError:
                pass
    return None


def _parse_contract_duration_original(notice_text: str | None) -> tuple[float | None, str | None]:
    if not notice_text:
        return None, None

    match = re.search(
        r"Duration of Contract</b><br/><br/>\s*([0-9][0-9,\.]*)\s*(Day|Week|Month|Year)\(s\)",
        notice_text,
        flags=re.IGNORECASE,
    )
    if match:
        return _parse_duration_number(match.group(1)), match.group(2).title()

    match = re.search(r"([0-9][0-9,\.]*)\s*(Day|Week|Month|Year)\(s\)", notice_text, flags=re.IGNORECASE)
    if match:
        return _parse_duration_number(match.group(1)), match.group(2).title()

    return None, None


def _is_leap_year(year: int | None) -> bool:
    if year is None:
        return False
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _parse_duration_number(value: str) -> float | None:
    cleaned = value.strip().replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_contract_duration_days(notice_text: str | None, year_awarded: int | None) -> int | None:
    if not notice_text:
        return None

    match = re.search(
        r"Duration of Contract</b><br/><br/>\s*([0-9][0-9,\.]*)\s*(Day|Week|Month|Year)\(s\)",
        notice_text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(r"([0-9][0-9,\.]*)\s*(Day|Week|Month|Year)\(s\)", notice_text, flags=re.IGNORECASE)
    if not match:
        return None

    raw_value = _parse_duration_number(match.group(1))
    if raw_value is None:
        return None

    unit = match.group(2).lower()
    days_in_year = 366 if _is_leap_year(year_awarded) else 365
    if unit == "day":
        return int(round(raw_value))
    if unit == "week":
        return int(round(raw_value * 7))
    if unit == "month":
        return int(round(raw_value * (days_in_year / 12.0)))
    if unit == "year":
        return int(round(raw_value * days_in_year))
    return None


def _parse_award_date(notice_text: str | None) -> str | None:
    if not notice_text:
        return None
    match = re.search(r"Date Notification of Award Issued.*?(\d{4}/\d{2}/\d{2})", notice_text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1)
    return None


def _extract_section(notice_text: str | None, header: str, next_headers: list[str]) -> str | None:
    if not notice_text:
        return None
    header_match = re.search(re.escape(header), notice_text, flags=re.IGNORECASE)
    if not header_match:
        return None
    start = notice_text.find("<div class='row col-sm-12'>", header_match.end())
    if start == -1:
        start = header_match.end()
    end = len(notice_text)
    for next_header in next_headers:
        next_match = re.search(re.escape(next_header), notice_text[start:], flags=re.IGNORECASE)
        if next_match:
            end = min(end, start + next_match.start())
    return notice_text[start:end]


def _extract_award_section(notice_text: str | None) -> str | None:
    if not notice_text:
        return None
    header_match = re.search(r"Awarded (?:Bidder|Firm)\(s\):", notice_text, flags=re.IGNORECASE)
    if not header_match:
        return None
    start = notice_text.find("<div class='row col-sm-12'>", header_match.end())
    if start == -1:
        start = header_match.end()
    end = len(notice_text)
    for next_header in [
        r"Evaluated\s+(?:Bidder|Firm)\(s\):",
        r"Date\s+Notification\s+of\s+Award\s+Issued",
    ]:
        next_match = re.search(next_header, notice_text[start:], flags=re.IGNORECASE)
        if next_match:
            end = min(end, start + next_match.start())
    return notice_text[start:end]


def _extract_evaluated_section(notice_text: str | None) -> str | None:
    if not notice_text:
        return None
    header_match = re.search(r"Evaluated\s+(?:Bidder|Firm)\(s\):", notice_text, flags=re.IGNORECASE)
    if not header_match:
        return None
    start = notice_text.find("<div class='row col-sm-12'>", header_match.end())
    if start == -1:
        start = header_match.end()
    end = len(notice_text)
    for next_header in [
        r"Awarded\s+(?:Bidder|Firm)\(s\):",
        r"Date\s+Notification\s+of\s+Award\s+Issued",
    ]:
        next_match = re.search(next_header, notice_text[start:], flags=re.IGNORECASE)
        if next_match:
            end = min(end, start + next_match.start())
    return notice_text[start:end]


def _parse_party_rows(section_text: str | None) -> list[tuple[str | None, str | None]]:
    if not section_text:
        return []
    row_marker = "<div class='row col-sm-12'><div class='col-sm-5'><div class='row col-sm-12'>"
    starts = [match.start() for match in re.finditer(re.escape(row_marker), section_text, flags=re.IGNORECASE)]
    parsed: list[tuple[str | None, str | None]] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(section_text)
        block = section_text[start:end]
        left_end = block.find("</div></div><div class='col-sm-7'>")
        if left_end == -1:
            left_end = len(block)
        left_text = block[:left_end]
        right_text = block[left_end:]

        name_match = re.search(r"<b>\s*([^<]+?)\s*(?:\(\d+\))?\s*</b>", left_text, flags=re.IGNORECASE | re.DOTALL)
        cleaned_name = _normalize_text(name_match.group(1)) if name_match else None
        country_match = re.search(r"Country:\s*([^<\r\n<]+)", left_text, flags=re.IGNORECASE)
        cleaned_country = _normalize_text(country_match.group(1)) if country_match else None
        if not cleaned_name:
            continue
        low_name = cleaned_name.lower()
        if low_name in {"awarded bidder(s)", "evaluated bidder(s)", "awarded firm(s)", "evaluated firm(s)"}:
            continue
        if "beneficial ownership" in low_name:
            continue
        parsed.append((cleaned_name, cleaned_country or None))
    return parsed


def _parse_award_party_info(notice_text: str | None) -> tuple[str | None, str | None]:
    section = _extract_award_section(notice_text)
    if not section:
        return None, None

    rows = _parse_party_rows(section)
    if rows:
        first_name, first_country = rows[0]
        return first_name, first_country

    matches = re.findall(
        r"<b>\s*([^<]+?)\s*(?:\(\d+\))?\s*</b>(?:(?!<b>).){0,500}?Country:\s*([^<\r\n<]+)",
        section,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not matches:
        return None, None

    filtered: list[tuple[str, str]] = []
    for raw_name, raw_country in matches:
        name = _normalize_text(raw_name)
        country = _normalize_text(raw_country)
        if not name:
            continue
        if "beneficial ownership" in name.lower():
            continue
        filtered.append((name, country))

    if not filtered:
        return None, None

    first_name, first_country = filtered[0]
    return first_name, first_country


def _parse_winning_firm_name(notice_text: str | None) -> str | None:
    names, _ = _parse_award_party_info(notice_text)
    values = _split_semicolon_values(names)
    return values[0] if values else None


def _parse_winning_firm_country(notice_text: str | None) -> str | None:
    _, countries = _parse_award_party_info(notice_text)
    values = _split_semicolon_values(countries)
    return values[0] if values else None


def _parse_winning_firm_code(notice_text: str | None) -> str | None:
    section = _extract_award_section(notice_text)
    if not section:
        return None

    # Prefer the first bidder row block to avoid matching unrelated table headers.
    row_match = re.search(
        r"<div class='row col-sm-12'><div class='col-sm-5'><div class='row col-sm-12'>\s*<b>\s*[^<]+?\((\d+)\)\s*</b>",
        section,
        flags=re.IGNORECASE,
    )
    if row_match:
        return row_match.group(1)

    fallback_match = re.search(r"<b>\s*[^<]+?\((\d+)\)\s*</b>.*?Country:", section, flags=re.IGNORECASE | re.DOTALL)
    if fallback_match:
        return fallback_match.group(1)
    return None


def _parse_bidder_country(notice_text: str | None) -> str | None:
    section = _extract_evaluated_section(notice_text)
    rows = _parse_party_rows(section)
    countries = [country for _, country in rows if country]
    return "; ".join(countries) or None


def _parse_bidder_price_currency_and_amount(notice_text: str | None) -> tuple[str | None, str | None]:
    section = _extract_evaluated_section(notice_text)
    if not section:
        return None, None
    row_marker = "<div class='row col-sm-12'><div class='col-sm-5'><div class='row col-sm-12'>"
    starts = [match.start() for match in re.finditer(re.escape(row_marker), section, flags=re.IGNORECASE)]
    matches: list[tuple[str, str]] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(section)
        block = section[start:end]
        left_end = block.find("</div></div><div class='col-sm-7'>")
        if left_end == -1:
            left_end = len(block)
        right_text = block[left_end:]
        price_match = re.search(r"Evaluated Bid Price<br/>\s*([A-Z]{2,3})\s*([0-9][0-9,\.]*)", right_text, flags=re.IGNORECASE)
        if price_match:
            matches.append((price_match.group(1), price_match.group(2)))
    if not matches:
        return None, None
    currencies = [currency.upper() for currency, _ in matches]
    amounts = [_normalize_text(amount) for _, amount in matches]
    return "; ".join(currencies) or None, "; ".join(amounts) or None


def _parse_winning_firm_is_chinese(winning_firm_country: str | None) -> int | None:
    if not winning_firm_country:
        return None
    normalized = winning_firm_country.strip().lower()
    if normalized in {"china", "prc", "people's republic of china", "people republic of china"} or "china" in normalized:
        return 1
    return 0


def _parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_contract_currency_and_amount(notice: dict[str, Any]) -> tuple[str | None, float | None]:
    notice_text = notice.get("notice_text")
    if notice_text:
        match = re.search(
            r"Evaluated Bid Price<br/>\s*([A-Z]{3})\s*([0-9][0-9,\.]*)",
            notice_text,
            flags=re.IGNORECASE,
        )
        if match:
            currency = match.group(1).upper()
            amount = _parse_float(match.group(2))
            if amount is not None:
                return currency, amount

    currency_code = notice.get("bid_currency_code")
    amount_value = _parse_float(notice.get("bid_estimate_amount"))
    if currency_code and amount_value is not None:
        return str(currency_code).upper(), amount_value
    if currency_code:
        return str(currency_code).upper(), None
    return None, amount_value


def _build_contract_url(record_id: str | None) -> str | None:
    if not record_id:
        return None
    return f"{_PROCUREMENT_DETAIL_BASE_URL}/{record_id}"


def _derive_firm_registered_locally(winning_firm_country: str | None, project_country: str | None) -> int | None:
    if not winning_firm_country:
        return None
    if not project_country:
        return None

    project_country_normalized = _normalize_text(project_country).lower()
    winning_countries = _split_semicolon_values(winning_firm_country)
    if not winning_countries:
        return None

    normalized_winning = [_normalize_text(item).lower() for item in winning_countries]
    return 1 if all(item == project_country_normalized for item in normalized_winning) else 0


def _split_semicolon_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def _parse_price_number(value: str) -> float | None:
    cleaned = value.strip().replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _derive_bidder_metrics(
    bidder_country: str | None,
    bidder_price: str | None,
    winning_firm_name: str | None,
) -> tuple[int | None, int | None, str | None, str | None]:
    bidder_countries = _split_semicolon_values(bidder_country)
    bidder_prices = _split_semicolon_values(bidder_price)

    if bidder_countries:
        number_of_bidders = len(bidder_countries)
    elif winning_firm_name:
        # If evaluated bidder list is absent but winner exists, treat as single bidder.
        number_of_bidders = 1
    else:
        number_of_bidders = None

    if number_of_bidders is None:
        if_single_bidder = None
    else:
        if_single_bidder = 1 if number_of_bidders == 1 else 0

    lowest_country: str | None = None
    lowest_price: str | None = None
    if bidder_countries and bidder_prices:
        bound = min(len(bidder_countries), len(bidder_prices))
        candidates: list[tuple[float, int]] = []
        for idx in range(bound):
            numeric = _parse_price_number(bidder_prices[idx])
            if numeric is not None:
                candidates.append((numeric, idx))
        if candidates:
            # Stable tie-break: first occurrence in source order.
            _, best_idx = min(candidates, key=lambda x: (x[0], x[1]))
            lowest_country = bidder_countries[best_idx]
            lowest_price = bidder_prices[best_idx]

    return number_of_bidders, if_single_bidder, lowest_country, lowest_price


def fetch_world_bank_notices(
    start_year: int = 2015,
    end_year: int = 2024,
    rows: int = DEFAULT_ROWS_PER_PAGE,
    limit: int | None = None,
    notice_type: str | None = "Contract Award",
    deduplicate_projects: bool = True,
) -> list[ProcurementRecord]:
    records: list[ProcurementRecord] = []
    seen_record_ids: set[str] = set()
    seen_project_keys: set[str] = set()

    if notice_type is None:
        countries = get_lac_countries()
        for country_name in countries:
            country_records = _fetch_world_bank_notices_for_scope(
                start_year=start_year,
                end_year=end_year,
                rows=rows,
                limit=limit,
                country_name=country_name,
                notice_type=None,
                deduplicate_projects=deduplicate_projects,
                seen_record_ids=seen_record_ids,
                seen_project_keys=seen_project_keys,
            )
            records.extend(country_records)
            if limit is not None and len(records) >= limit:
                return records
        return records

    return _fetch_world_bank_notices_for_scope(
        start_year=start_year,
        end_year=end_year,
        rows=rows,
        limit=limit,
        country_name=None,
        notice_type=notice_type,
        deduplicate_projects=deduplicate_projects,
        seen_record_ids=seen_record_ids,
        seen_project_keys=seen_project_keys,
    )


def _fetch_world_bank_notices_for_scope(
    start_year: int,
    end_year: int,
    rows: int,
    limit: int | None,
    country_name: str | None,
    notice_type: str | None,
    deduplicate_projects: bool,
    seen_record_ids: set[str],
    seen_project_keys: set[str],
) -> list[ProcurementRecord]:
    records: list[ProcurementRecord] = []

    page = 0
    while True:
        params = {
            "format": "json",
            "fl": "*",
            "rows": str(rows),
            "os": str(page * rows),
            "apilang": "en",
        }
        if country_name:
            params["project_ctry_name_exact"] = country_name
        else:
            params["regionname_exact"] = "Latin America And Caribbean"
        if notice_type:
            params["notice_type_exact"] = notice_type
        url = f"{WORLD_BANK_NOTICES_API}?{urlencode(params)}"
        try:
            payload = _json_get_with_retry(url)
        except Exception:
            break

        notices = payload.get("procnotices", [])
        if not notices:
            break

        # Filter by year before detail requests to avoid unnecessary detail API calls.
        filtered_notices: list[dict[str, Any]] = []
        for notice in notices:
            notice_id = notice.get("id")
            if notice_id and notice_id in seen_record_ids:
                continue
            year_awarded = _parse_award_year(notice)
            if year_awarded is None:
                continue
            if not (start_year <= year_awarded <= end_year):
                continue
            filtered_notices.append(notice)

        if filtered_notices:
            with ThreadPoolExecutor(max_workers=_DETAIL_WORKERS) as executor:
                merged_notices = list(executor.map(_merge_notice_with_detail, filtered_notices))

            for merged_notice in merged_notices:
                record = _to_record(merged_notice)
                if record.year_awarded is None:
                    continue
                if not (start_year <= record.year_awarded <= end_year):
                    continue
                if record.record_id and record.record_id in seen_record_ids:
                    continue

                if deduplicate_projects:
                    # Keep one observation per project. If project_id is missing,
                    # fall back to record_id so such rows can still be retained.
                    project_key = record.project_id or record.record_id
                    if not project_key:
                        continue
                    if project_key in seen_project_keys:
                        continue
                    seen_project_keys.add(project_key)

                if record.record_id:
                    seen_record_ids.add(record.record_id)
                records.append(record)
                if limit is not None and len(records) >= limit:
                    return records

        page += 1
        if page * rows >= int(payload.get("total", 0)):
            break

    return records


def get_lac_countries() -> list[str]:
    payload = _json_get_with_retry(f"{WORLD_BANK_COUNTRY_API}?format=json&per_page=400")
    countries: list[str] = []
    for item in payload[1]:
        if (item.get("region") or {}).get("id") == "LCN" and item.get("id") not in {"LCN", "WLD"}:
            countries.append(item["name"])
    return sorted(set(countries))


def _to_record(notice: dict[str, Any]) -> ProcurementRecord:
    notice_text = notice.get("notice_text")
    country = notice.get("project_ctry_name")
    procurement_method = notice.get("procurement_method_name")
    bidder_count = _parse_number_of_bidders(notice_text)
    sector = _extract_sector(notice)
    year_awarded = _parse_award_year(notice)
    contract_currency, contract_amount = _parse_contract_currency_and_amount(notice)
    contract_duration_original, contract_duration_original_unit = _parse_contract_duration_original(notice_text)
    record_id = notice.get("id")
    date_awarded = _parse_award_date(notice_text)
    winning_firm_name = _parse_winning_firm_name(notice_text)
    winning_firm_code = _parse_winning_firm_code(notice_text)
    winning_firm_country = _parse_winning_firm_country(notice_text)
    firm_registered_locally = _derive_firm_registered_locally(winning_firm_country, country)
    bidder_country = _parse_bidder_country(notice_text)
    bidder_price_currency, bidder_price = _parse_bidder_price_currency_and_amount(notice_text)
    number_of_bidders, if_single_bidder, bidder_country_lowest_price, bidder_lowest_price = _derive_bidder_metrics(
        bidder_country,
        bidder_price,
        winning_firm_name,
    )
    return ProcurementRecord(
        project_id=notice.get("project_id"),
        notice_type=notice.get("notice_type"),
        notice_no=record_id,
        country=country,
        year_awarded=year_awarded,
        date_awarded=date_awarded,
        data_source="World Bank",
        procurement_channel="MDB-financed",
        funding_source=_extract_funding_source(notice),
        sector=sector,
        project_type=_infer_project_type(notice),
        contract_value_usd=None,
        contract_currency=contract_currency,
        contract_amount=contract_amount,
        contract_duration_original_unit=contract_duration_original_unit,
        contract_duration_original=contract_duration_original,
        contract_duration_days=_parse_contract_duration_days(notice_text, year_awarded),
        winning_firm_name=winning_firm_name,
        winning_firm_code=winning_firm_code,
        winning_firm_country=winning_firm_country,
        winning_firm_is_chinese=_parse_winning_firm_is_chinese(winning_firm_country),
        winning_firm_is_soe=_infer_winning_firm_is_soe(notice_text),
        number_of_bidders=number_of_bidders,
        if_single_bidder=if_single_bidder,
        bidder_country_lowest_price=bidder_country_lowest_price,
        bidder_lowest_price=bidder_lowest_price,
        bidder_country=bidder_country,
        bidder_price_currency=bidder_price_currency,
        bidder_price=bidder_price,
        procurement_method=procurement_method,
        financing_linked_to_bid=_infer_financing_linked_to_bid(notice_text),
        financing_source_chinese=_infer_financing_source_chinese(notice),
        joint_venture=_parse_joint_venture(notice_text),
        firm_registered_locally=firm_registered_locally,
        record_id=record_id,
        awarded_date=date_awarded,
        bid_reference_no=notice.get("bid_reference_no"),
        project_name=notice.get("project_name"),
        contract_url=_build_contract_url(record_id),
    )


def _extract_funding_source(notice: dict[str, Any]) -> str | None:
    credit = notice.get("credit") or []
    financing_ids = [entry.get("financing_id") for entry in credit if entry.get("financing_id")]
    return ", ".join(financing_ids) or None


def _parse_contract_value_usd(notice: dict[str, Any]) -> float | None:
    value = notice.get("bid_estimate_amount")
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _infer_project_type(notice: dict[str, Any]) -> str | None:
    group = notice.get("procurement_group_desc")
    if not group:
        return None
    group_lower = str(group).lower()
    if "consult" in group_lower:
        return "consulting"
    if "goods" in group_lower:
        return "goods"
    if "work" in group_lower or "construction" in group_lower:
        return "works"
    return None


def _extract_sector(notice: dict[str, Any]) -> str | None:
    major_sector = notice.get("procurement_major_sector_name")
    if major_sector:
        return str(major_sector)
    sector = notice.get("sector") or []
    if isinstance(sector, list):
        descriptions = [item.get("sector_description") for item in sector if item.get("sector_description")]
        if descriptions:
            return "; ".join(descriptions)
    notice_text = _normalize_text(notice.get("notice_text"))
    lower = notice_text.lower()
    if any(term in lower for term in ["road", "transport", "highway", "bridge"]):
        return "transport"
    if any(term in lower for term in ["energy", "electric", "power", "solar"]):
        return "energy"
    if any(term in lower for term in ["digital", "ict", "system", "software", "platform"]):
        return "ICT"
    return None


def _infer_winning_firm_is_chinese(notice_text: str | None) -> int | None:
    if not notice_text:
        return None
    lower = notice_text.lower()
    if any(token in lower for token in ["china", "chinese", "prc"]):
        return 1
    return None


def _infer_winning_firm_is_soe(notice_text: str | None) -> int | None:
    if not notice_text:
        return None
    lower = notice_text.lower()
    if any(token in lower for token in ["state-owned", "state owned", "soe", "state enterprise"]):
        return 1
    return None


def _infer_financing_linked_to_bid(notice_text: str | None) -> int | None:
    if not notice_text:
        return None
    lower = notice_text.lower()
    if any(token in lower for token in ["financing linked", "linked to bid", "bundled financing"]):
        return 1
    return None


def _infer_financing_source_chinese(notice: dict[str, Any]) -> int | None:
    financing_source = _extract_funding_source(notice)
    if not financing_source:
        return None
    lower = financing_source.lower()
    if any(token in lower for token in ["china", "chinese", "cdb", "exim", "imbank", "export-import"]):
        return 1
    return None


def _parse_number_of_bidders(notice_text: str | None) -> int | None:
    if not notice_text:
        return None
    match = re.search(r"(\d+)\s+bidders?", notice_text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _parse_joint_venture(notice_text: str | None) -> int | None:
    if not notice_text:
        return None
    lower = notice_text.lower()
    if "joint venture" in lower or "consortium" in lower:
        return 1
    return None


def to_dataframe(records: Iterable[ProcurementRecord]) -> pd.DataFrame:
    return pd.DataFrame([record.to_dict() for record in records])


def save_records(records: Iterable[ProcurementRecord], output_path: str) -> None:
    dataframe = to_dataframe(records)
    dataframe.to_csv(output_path, index=False, encoding="utf-8-sig")