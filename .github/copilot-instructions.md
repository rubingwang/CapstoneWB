CapstoneWB workspace instructions.

Project focus:
- Python package for procurement scraping
- Current target: World Bank procurement notices for Latin America and the Caribbean, 2015-2024
- Data source: official World Bank procurement API and World Bank country metadata API

Implementation notes:
- Prefer small, focused edits that preserve the existing package layout
- Keep CLI entry points stable under `capstonewb`
- Leave unavailable thesis variables as null rather than inventing values
- Treat inference helpers as best-effort only and keep them conservative

Verification notes:
- Run the package in editable mode during development
- Validate changes with a small sample scrape before larger runs
- Update the README when the schema or run instructions change
