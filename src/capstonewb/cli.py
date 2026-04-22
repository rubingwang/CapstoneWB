"""Command line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DEFAULT_END_YEAR, DEFAULT_OUTPUT_DIR, DEFAULT_START_YEAR
from .world_bank import fetch_world_bank_notices, save_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="capstonewb")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape = subparsers.add_parser("scrape-world-bank", help="Scrape World Bank procurement notices")
    scrape.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    scrape.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR)
    scrape.add_argument("--output", type=str, default=f"{DEFAULT_OUTPUT_DIR}/world_bank_lac_2015_2024.csv")
    scrape.add_argument("--limit", type=int, default=None)
    scrape.add_argument("--rows", type=int, default=500)
    scrape.add_argument("--all-notice-types", action="store_true", help="Do not filter by notice type")
    scrape.add_argument("--notice-level", action="store_true", help="Keep all notices (no project-level dedup)")
    scrape.set_defaults(func=_run_scrape_world_bank)

    return parser


def _run_scrape_world_bank(args: argparse.Namespace) -> int:
    records = fetch_world_bank_notices(
        start_year=args.start_year,
        end_year=args.end_year,
        limit=args.limit,
        rows=args.rows,
        notice_type=None if args.all_notice_types else "Contract Award",
        deduplicate_projects=not args.notice_level,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_records(records, str(output_path))
    print(f"Saved {len(records)} records to {output_path}")
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()