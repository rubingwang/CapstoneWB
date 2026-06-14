"""Caribbean Development Bank procurement scraping helpers."""

from __future__ import annotations

import html as html_module
import json
import re
import ssl
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

import pandas as pd
import requests

from .config import WORLD_BANK_COUNTRY_API


_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X) CapstoneWB/0.1"
_CDB_BASE_URL = "https://www.caribank.org/work-with-us/procurement/contract-awards"
_DEFAULT_YEARS = list(range(2012, 2027))
_SSL_CONTEXT = ssl._create_unverified_context()


@dataclass
class CDBContractAward:
    award_year: int | None = None
    notice_id: str | None = None
    project_name: str | None = None
    sector: str | None = None
    country: str | None = None
    procurement_type: str | None = None
    winning_bid_raw: str | None = None
    winning_country: str | None = None
    winning_firm: str | None = None
    currency_unit: str | None = None
    contract_amount: float | None = None
    contract_value_usd: float | None = None
    notice_url: str | None = None
    page_url: str | None = None
    data_source: str | None = "CDB"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=30, context=_SSL_CONTEXT) as response:
        return response.read().decode("utf-8", "ignore")


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def _extract_select_options(html_text: str, select_name: str) -> list[tuple[str, str]]:
    match = re.search(
        rf'<select[^>]+name="{re.escape(select_name)}"[^>]*>(.*?)</select>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []
    select_block = match.group(1)
    options = re.findall(r'<option[^>]+value="([^"]*)"[^>]*>(.*?)</option>', select_block, flags=re.IGNORECASE | re.DOTALL)
    cleaned: list[tuple[str, str]] = []
    for value, label in options:
        cleaned.append((_normalize_text(value), _normalize_text(html_module.unescape(label))))
    return cleaned


def get_cdb_years() -> list[int]:
    html_text = _get_html(_CDB_BASE_URL)
    years: list[int] = []
    for value, _label in _extract_select_options(html_text, "solr_publication_contract_awards_years_filter"):
        if value.isdigit():
            years.append(int(value))
    if years:
        return sorted(set(years), reverse=True)
    return list(reversed(_DEFAULT_YEARS))


def get_cdb_country_names() -> list[str]:
    html_text = _get_html(_CDB_BASE_URL)
    countries: list[str] = []
    for value, label in _extract_select_options(html_text, "field_cdb_country_tag"):
        if value and value != "All" and label:
            countries.append(label)
    return sorted(set(countries), key=lambda item: (-len(item), item.lower()))


def _country_variants(name: str) -> set[str]:
    variants = {name}
    if ", The" in name:
        variants.add("The " + name.replace(", The", ""))
    if name.startswith("Saint "):
        variants.add("St. " + name[len("Saint ") :])
        variants.add("St " + name[len("Saint ") :])
    if name.startswith("St. "):
        variants.add("Saint " + name[len("St. ") :])
        variants.add("St " + name[len("St. ") :])
    if "." in name:
        variants.add(name.replace(".", ""))
    return {variant for variant in variants if variant}


@lru_cache(maxsize=1)
def _global_country_names() -> list[str]:
    request = Request(f"{WORLD_BANK_COUNTRY_API}?format=json&per_page=400", headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(request, timeout=30, context=_SSL_CONTEXT) as response:
            payload = json.loads(response.read().decode("utf-8", "ignore"))
    except (HTTPError, URLError, json.JSONDecodeError):
        payload = [None, []]

    names: set[str] = set()
    for item in payload[1] or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name:
            continue
        if item.get("id") in {"LCN", "WLD"}:
            continue
        for variant in _country_variants(str(name)):
            names.add(variant)

    for alias in {
        "Hong Kong SAR, China",
        "Macao SAR, China",
        "West Bank and Gaza",
        "East Timor",
        "Cabo Verde",
        "The Bahamas",
        "St Maarten",
        "St. Maarten",
    }:
        names.add(alias)

    return sorted(names, key=len, reverse=True)


def _extract_table_rows(html_text: str) -> list[list[str]]:
    table_match = re.search(r"<table[^>]*>(.*?)</table>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not table_match:
        return []
    table_html = table_match.group(1)
    row_html_blocks = re.findall(r"<tr>(.*?)</tr>", table_html, flags=re.IGNORECASE | re.DOTALL)
    rows: list[list[str]] = []
    for row_html in row_html_blocks:
        if "<td" not in row_html.lower():
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.IGNORECASE | re.DOTALL)
        rows.append(cells)
    return rows


def _parse_anchor(cell_html: str) -> tuple[str | None, str | None, str | None]:
    href_match = re.search(r'<a[^>]+href="([^"]+)"', cell_html, flags=re.IGNORECASE)
    title_match = re.search(r'title="([^"]+)"', cell_html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", cell_html)
    text = _normalize_text(html_module.unescape(text))
    href = html_module.unescape(href_match.group(1)) if href_match else None
    title = _normalize_text(html_module.unescape(title_match.group(1))) if title_match else None
    return text or None, title or None, href or None


def _parse_amount_and_currency(text: str) -> tuple[str | None, float | None, str | None]:
    clean = _normalize_text(text)
    amount_match = re.search(r"(?P<amount>\d[\d,]*(?:\.\d+)?)$", clean)
    if not amount_match:
        return clean or None, None, None

    amount_text = amount_match.group("amount")
    prefix = clean[: amount_match.start("amount")].rstrip()
    currency_match = re.search(
        r"(?P<currency>(?:USD|EUR|GBP|CAD|BBD|BDS|BZE|XCD|JMD|TTD|GYD|SRD|EC\$|US\$|B\$|\$|Euros?|Euro|Dollar(?:s)?)|[A-Z]{2,5})(?:\s*\$)?\s*$",
        prefix,
        flags=re.IGNORECASE,
    )

    currency: str | None = None
    body = prefix
    if currency_match:
        currency = _normalize_text(currency_match.group("currency")) or None
        body = prefix[: currency_match.start("currency")].rstrip()

    try:
        amount = float(amount_text.replace(",", ""))
    except ValueError:
        amount = None

    return body or None, amount, currency


def _normalize_currency_unit(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = _normalize_text(value).upper().replace(".", "")
    cleaned = cleaned.replace("US$", "USD")
    cleaned = cleaned.replace("EUROS", "EUR").replace("EURO", "EUR")
    cleaned = cleaned.replace("BZE", "BZD")
    cleaned = cleaned.replace("BDS", "BBD")
    cleaned = cleaned.replace("EC$", "XCD").replace("EC", "XCD")

    if cleaned in {"$", "USD$"}:
        return "USD"
    if cleaned.startswith("USD"):
        return "USD"
    if cleaned.startswith("EUR"):
        return "EUR"
    if cleaned.startswith("GBP"):
        return "GBP"
    if cleaned.startswith("CAD"):
        return "CAD"
    if cleaned.startswith("BZD"):
        return "BZD"
    if cleaned.startswith("BBD"):
        return "BBD"
    if cleaned.startswith("XCD"):
        return "XCD"
    if cleaned.startswith("JMD"):
        return "JMD"
    if cleaned.startswith("TTD"):
        return "TTD"
    if cleaned.startswith("GYD"):
        return "GYD"
    if cleaned.startswith("SRD"):
        return "SRD"
    if cleaned.startswith("BSD"):
        return "BSD"
    if cleaned.startswith("HTG"):
        return "HTG"

    return cleaned if len(cleaned) <= 5 else None


@lru_cache(maxsize=None)
def _year_end_usd_rate(year: int, currency_code: str) -> float | None:
    currency_code = _normalize_currency_unit(currency_code)
    if not currency_code:
        return None
    if currency_code == "USD":
        return 1.0

    url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{year}-12-31/v1/currencies/{currency_code.lower()}.json"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        rate = payload[currency_code.lower()]["usd"]
        return float(rate)
    except Exception:
        return None


def _convert_to_usd(amount: float | None, year: int | None, currency_code: str | None) -> float | None:
    if amount is None:
        return None
    if year is None:
        return None
    rate = _year_end_usd_rate(year, currency_code or "")
    if rate is None:
        return None
    return round(float(amount) * rate, 2)


def _split_country_and_firm(body: str, country_names: list[str]) -> tuple[str | None, str | None]:
    clean = _normalize_text(body)
    if not clean:
        return None, None

    for country in country_names:
        escaped = re.escape(country)
        start_match = re.match(rf"^{escaped}\s*-\s*(?P<firm>.+)$", clean, flags=re.IGNORECASE)
        if start_match:
            return country, _normalize_text(start_match.group("firm")) or None

        end_match = re.match(rf"^(?P<firm>.+?)\s*-\s*{escaped}$", clean, flags=re.IGNORECASE)
        if end_match:
            return country, _normalize_text(end_match.group("firm")) or None

    return None, clean


def _extract_country_prefix(body: str, country_names: list[str]) -> tuple[list[str], str | None]:
    clean = _normalize_text(body)
    if not clean:
        return [], None

    remaining = clean
    countries: list[str] = []
    separator_pattern = re.compile(r"^[\s\-/:,;&]+")

    while remaining:
        stripped = separator_pattern.sub("", remaining).strip()
        if not stripped:
            remaining = ""
            break

        lowered = stripped.lower()
        matched_country: str | None = None
        for country in country_names:
            if lowered.startswith(country.lower()):
                matched_country = country
                if not countries or countries[-1].lower() != country.lower():
                    countries.append(country)
                remaining = stripped[len(country) :]
                break

        if matched_country is None:
            break

    return countries, _normalize_text(remaining) or None


def _parse_winning_bid(winning_bid_text: str | None, country_names: list[str]) -> tuple[str | None, str | None, str | None, float | None]:
    if not winning_bid_text:
        return None, None, None, None

    body, amount, currency = _parse_amount_and_currency(winning_bid_text)
    if not body:
        return None, None, currency, amount

    winning_countries, winning_firm = _extract_country_prefix(body, country_names)
    winning_country = "; ".join(winning_countries) or None
    return winning_country, winning_firm, currency, amount


def fetch_cdb_contract_awards(years: list[int] | None = None) -> list[CDBContractAward]:
    country_names = _global_country_names()
    years_to_fetch = years or get_cdb_years()
    records: list[CDBContractAward] = []

    for year in years_to_fetch:
        page = 0
        year_sequence = 0
        while True:
            params = {"solr_publication_contract_awards_years_filter": str(year)}
            if page:
                params["page"] = str(page)
            page_url = f"{_CDB_BASE_URL}?{urlencode(params)}"
            html_text = _get_html(page_url)
            rows = _extract_table_rows(html_text)
            if not rows:
                break

            for row_cells in rows:
                if len(row_cells) < 5:
                    continue

                title_text, title_attr, href = _parse_anchor(row_cells[0])
                sector = _normalize_text(re.sub(r"<[^>]+>", " ", row_cells[1])) or None
                country = _normalize_text(re.sub(r"<[^>]+>", " ", row_cells[2])) or None
                procurement_type = _normalize_text(re.sub(r"<[^>]+>", " ", row_cells[3])) or None
                winning_bid_raw = _normalize_text(re.sub(r"<[^>]+>", " ", row_cells[4])) or None
                winning_country, winning_firm, currency_unit, contract_amount = _parse_winning_bid(winning_bid_raw, country_names)
                year_sequence += 1
                contract_value_usd = _convert_to_usd(contract_amount, year, currency_unit)

                records.append(
                    CDBContractAward(
                        award_year=year,
                        notice_id=f"CDB{year}-{year_sequence:03d}",
                        project_name=title_text or title_attr,
                        sector=sector,
                        country=country,
                        procurement_type=procurement_type,
                        winning_bid_raw=winning_bid_raw,
                        winning_country=winning_country,
                        winning_firm=winning_firm,
                        currency_unit=currency_unit,
                        contract_amount=contract_amount,
                        contract_value_usd=contract_value_usd,
                        notice_url=urljoin(_CDB_BASE_URL, href) if href else None,
                        page_url=page_url,
                    )
                )

            page += 1

    return records


def to_dataframe(records: list[CDBContractAward]) -> pd.DataFrame:
    return pd.DataFrame([record.to_dict() for record in records])


def save_records(records: list[CDBContractAward], output_path: str) -> None:
    dataframe = to_dataframe(records)
    dataframe.to_csv(output_path, index=False, encoding="utf-8-sig")
