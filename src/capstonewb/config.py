"""Project configuration and defaults."""

from __future__ import annotations

from dataclasses import dataclass


WORLD_BANK_NOTICES_API = "https://search.worldbank.org/api/v2/procnotices"
WORLD_BANK_COUNTRY_API = "https://api.worldbank.org/v2/country"

LAC_REGION_ID = "LCN"
LAC_REGION_LABEL = "Latin America And Caribbean"

DEFAULT_START_YEAR = 2015
DEFAULT_END_YEAR = 2024
DEFAULT_ROWS_PER_PAGE = 500
DEFAULT_OUTPUT_DIR = "data"


@dataclass(frozen=True)
class ScrapeWindow:
    """Inclusive year window for the scraper."""

    start_year: int = DEFAULT_START_YEAR
    end_year: int = DEFAULT_END_YEAR