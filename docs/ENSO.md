# El Niño / La Niña tracker

Open `/enso/`. Generate the official-source snapshot with:

```bash
python -m enso
```

Uses existing Python dependencies and Ubuntu setup from `docs/SUNSET.md`. No required environment variables, credentials, API keys, GUI or manual login. The existing 8 a.m. America/New_York workflow now runs this command before export/deployment. Refresh in the browser checks the latest published snapshot; it does not trigger a source update or generate a new ENSO declaration.

## Sources and scientific distinctions

The **official ENSO alert status and synopsis** are parsed from the NOAA/CPC ENSO Diagnostic Discussion, with its actual issue date and next scheduled date when published. Status is never inferred from a single index value or from automatic ±0.5°C classification. Watches, advisories and inactive status remain the exact official wording.

NOAA began operational RONI use in February 2026. The Relative Oceanic Niño Index subtracts the tropical-mean SST anomaly from Niño 3.4 anomalies, with variance adjustment, and is based on overlapping three-month means. The current CPC RONI historical page describes ERSSTv6 and 1991–2020 reference conditions. This tracker reads NOAA's maintained index, rather than attempting to reproduce that calculation.

- RONI: `https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt`.
- Traditional ONI comparison: `https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt`. It is a distinct index and is not presented as the operational status decision.
- Weekly conventional Niño 3.4 SST and anomaly: `https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for`. Weekly observations are dated by the center of the week and use the 1991–2020 climatology. They are **not weekly RONI** and do not independently establish ENSO status.
- Official discussion: `https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml`.
- Official RONI forecast: `https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/outlook/`; preserve the published chart including its issue month, seasons, mean and middle 50/70/90% forecast ranges. These are index forecast ranges, not local weather-impact probabilities.

The observed chart has RONI and optional ONI comparison, 3/10/30-year or full history, a mouse/keyboard season readout and CSV export of both series. No forecast points are appended to the observed series. The ±0.5°C lines are reference thresholds; NOAA historical episode classification involves at least five consecutive overlapping seasons and atmosphere–ocean coupling. The official alert card is always sourced from the discussion. Weekly anomalies have a separate last-52-week chart without RONI threshold bands.

RONI/ONI season years identify the central month: DJF 2026 is December 2025 through February 2026. The interface spells out these calendar intervals. Missing index sentinels remain null and create chart gaps rather than zero values. The most recent seasonal values are estimates and can be revised. No decimal place beyond the provider's precision is invented for the weekly value. CSV columns retain explicit center year, season, center month, RONI and ONI.

A daily website refresh does not imply a daily update to a monthly index or discussion. The page separately dates generation, official discussion, index season, weekly observation, and outlook issue month. Snapshots older than 48 hours or discussions older than 50 days receive an older-data notice. A missing feed leaves the previous successful hosted publication in place. If browser metadata is unavailable, cards and charts clear to unavailable; the status never defaults to ENSO-neutral. The source links remain available.

## Pipeline reliability

Bound text sources to 1 MB each, chart to 8 MB, with request timeouts and bounded retries. Validate seasonal columns, duplicate seasons, missing sentinels, plausible values, minimum history length and monitoring dates. The weekly parser handles adjacent signed fields such as `26.5-0.2` without shifting the Niño 3.4 columns. Required status/date/synopsis or forecast-graphic markup changes cause nonzero failure instead of a guessed status. The original NOAA chart PNG is validated and preserved byte-for-byte. Hash-based graphic filenames avoid mixing an old manifest with a newer image. Stage before publication and write the manifest last; a failed hosted build does not replace the last successful Pages deployment.

Outputs: `generated/enso/latest.json` (official status/synopsis, dates, observed series, sources, chart metadata/hash) and `roni-outlook-YYYYMM-HASH.png`. All data come from NOAA/CPC. No local seasonal forecast is created and no ENSO phase is advertised as a guarantee for Carolina weather.

Primary references: [NOAA ENSO](https://www.noaa.gov/understanding-el-nino), [CPC RONI method and revisions](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/), [official discussion](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml), [official outlook](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/outlook/).

## Exact files added or replaced

Added: `enso/__init__.py`, `enso/__main__.py`, `enso/index.html`, `assets/enso.js`, `assets/enso.css`, `tests/test_enso.py`, `docs/ENSO.md`, `generated/enso/latest.json`, and the hash-named official outlook PNG identified in that manifest.

Replaced: `index.html`, `outlooks/index.html`, `outlooks/centers.html`, `models/index.html` (tracker links); `.github/workflows/sunset.yml` (generation step, push path, artifact); `scripts/package_site.py`, `scripts/package_github.py` (packaging); `README.md`, `docs/REFRESHES.md`; `output/ch-weather-github-ready.zip`, `output/ch-weather-website.zip`. Matching `_site/` preview assets are refreshed. Existing model, sunset and analysis calculations are unchanged.

Upload the extracted source package with folders preserved, including the new `enso/` Python files and updated workflow. Keep the existing CNAME. No new secret. Source ZIP excludes generated outputs; Actions generates them before export. GitHub browser uploads may require two batches because the complete source package exceeds 100 files.

## Verification

Generated the snapshot from real CPC discussion, RONI, ONI, weekly SST and forecast-chart sources. Checked the official issue date and exact status, latest seasonal/weekly values with distinct dates, since-1950 chart range, DJF cross-year dates, ONI comparison, CSV download and 390-pixel mobile layout. Parser tests cover missing seasonal values, duplicate seasons, adjacent negative weekly fields, and exact official status/synopsis extraction without threshold-based classification.
