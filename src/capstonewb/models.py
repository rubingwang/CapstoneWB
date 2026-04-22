"""Shared data structures for procurement records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(slots=True)
class ProcurementRecord:
    project_id: str | None = None
    notice_type: str | None = None
    notice_no: str | None = None
    country: str | None = None
    year_awarded: int | None = None
    date_awarded: str | None = None
    data_source: str | None = None
    procurement_channel: str | None = None
    funding_source: str | None = None
    sector: str | None = None
    project_type: str | None = None
    contract_value_usd: float | None = None
    contract_currency: str | None = None
    contract_amount: float | None = None
    contract_duration_original_unit: str | None = None
    contract_duration_original: float | None = None
    contract_duration_days: int | None = None
    winning_firm_name: str | None = None
    winning_firm_code: str | None = None
    winning_firm_country: str | None = None
    winning_firm_is_chinese: int | None = None
    winning_firm_is_soe: int | None = None
    number_of_bidders: int | None = None
    if_single_bidder: int | None = None
    bidder_country_lowest_price: str | None = None
    bidder_lowest_price: str | None = None
    bidder_country: str | None = None
    bidder_price_currency: str | None = None
    bidder_price: str | None = None
    procurement_method: str | None = None
    financing_linked_to_bid: int | None = None
    financing_source_chinese: int | None = None
    joint_venture: int | None = None
    firm_registered_locally: int | None = None
    record_id: str | None = None
    awarded_date: str | None = None
    bid_reference_no: str | None = None
    project_name: str | None = None
    contract_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def records_to_dicts(records: Iterable[ProcurementRecord]) -> list[dict[str, Any]]:
    return [record.to_dict() for record in records]