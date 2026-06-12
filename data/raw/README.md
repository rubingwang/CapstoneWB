# Raw Data Layout

This branch keeps the old World Bank thesis project intact and starts a new source-separated raw data flow.

Planned raw CSV locations:

- `data/raw/world_bank/world_bank_lac_raw.csv`
- `data/raw/idb/idb_lac_raw.csv`
- `data/raw/cdb/cdb_lac_raw.csv`

Rules:

- Keep one raw CSV per source.
- Do not overwrite the old merged thesis datasets in `data/`.
- Keep source-specific outputs conservative and source-native; do not merge before the raw layer is complete.

This directory is intentionally separate from the earlier World Bank-only deliverables.