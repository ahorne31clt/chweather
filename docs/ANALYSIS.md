# RTMA surface analysis and METAR station plots

Open `/analysis/`. Generate with the existing pinned Python dependencies:

```bash
python -m analysis
```

No additional dependencies, environment variables, credentials, GUI or login. Ubuntu installation is unchanged from `docs/SUNSET.md`. The existing 8 a.m. America/New_York workflow now runs this command before the model/export/deploy steps. These are published analysis snapshots, not continuously streaming observations. Refresh checks the website's latest snapshot, not NOAA directly. Analysis older than three hours is marked as an older snapshot. To obtain a new analysis, run the command locally or dispatch the updated workflow.

## Analysis data

Public NOMADS RTMA 2.5 CONUS western-expansion `2dvaranl_ndfd.grb2_wexp`, filtered to instantaneous 2 m temperature/dewpoint and 10 m sustained wind/gust speed. Select the previous UTC hour to allow publication, then at most two earlier hours; no synthetic fallback. Validate initialization, zero lead, level, units, Lambert grid, approximately 2.5 km spacing, missing fraction and plausible bounds. Native spacing of this NOAA grid is about 2539.703 m, not an invented 1-km grid. Analysis is not a forecast or raw station observation.

Maps: temperature/dewpoint in °F; sustained wind and gust speed in knots; derived relative humidity in percent (Magnus formula using RTMA temperature and dewpoint, clipped 0–100); and stations-only background. Native fields are rendered without artificial added resolution, with dark country/state boundaries. Two independently rendered regions: CONUS and Carolinas. Twelve 2400 × 1350 PNGs are generated. Station positions are calculated in each map projection, with true-direction wind vectors rotated into map coordinates.

## Station data and symbols

Download NOAA/AWC's recommended full METAR CSV gzip cache once per generation. Keep the latest report per station on CONUS land, no more than two hours old at retrieval and within 90 minutes of RTMA valid time. Future reports beyond five minutes and invalid coordinates/values are rejected. At least 100 recent stations are required to publish; the first real run had over 2,300. Each station retains its exact observation time, raw METAR, temperature/dewpoint, sustained wind/direction/gust, reported sea-level pressure, altimeter setting, visibility and present weather. Analysis valid time and observation-time range are shown separately; the stations are not all simultaneous with each other or RTMA.

Station plots show °F temperature upper left, °F dewpoint lower left, reported sea-level pressure upper right as the final three digits of hPa × 10, sky-cover circle and sustained-wind barb. Missing SLP is omitted; **altimeter is never substituted or converted into SLP**. Sea-level pressure, altimeter and gust remain explicit in the station details. METAR cloud columns repeat in the CSV, so all layers are read before choosing the greatest cover category. Representative sky symbols use CLR/SKC 0, FEW 1/8, SCT 3/8, BKN 6/8, OVC/VV full; they do not claim an exact measured cloud fraction. Unknown cover is ×; an outer circle means calm. Variable direction is VRB, not calm. Half/full/flag barbs represent 5/10/50 kt, rounded to nearest 5 kt.

Hover, tap, or focus a station for its values, timestamp and raw report. The density selector declutters by display distance. Zoom and pan keep station locations registered to the map. Station code search includes the selected station even if decluttering would otherwise omit it, and switches to CONUS when needed. Station overlay can be toggled. PNG export combines the selected analysis, visible station symbols and time-range attribution. Missing values remain missing, not zero. Gridded point-value sampling is not included in this version.

## Reliability and files

Bound RTMA downloads to 30 MB, station gzip to 4 MB and decompressed CSV to 12 MB. HTTPS requests have timeouts and bounded retries. Rendering uses Matplotlib Agg with no windows. Generate all files in a temporary folder, publish manifest last, and return nonzero on download/processing/render failure. A failed hosted build leaves the previous Pages deployment in place. Station JSON has a SHA-256 hash checked by the browser before display.

Outputs: `generated/analysis/latest.json`, `stations.json`, and `{conus,carolinas}-{temperature,dewpoint,humidity,wind,gust,stations}.png`. JSON identifies analysis UTC, generation UTC, station-time range, sources, dimensions, native spacing and image hashes. No station observations are fabricated from the grid.

Sources: [NOAA RTMA inventory](https://www.nco.ncep.noaa.gov/pmb/products/rtma/), [EMC RTMA description](https://emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/rtma.php), [AWC API/cache documentation](https://aviationweather.gov/data/api/), [METAR cache](https://aviationweather.gov/data/cache/metars.cache.csv.gz), Natural Earth boundaries.

## Exact files added or replaced

Added: `analysis/__init__.py`, `analysis/data.py`, `analysis/render.py`, `analysis/__main__.py`, `analysis/index.html`, `assets/analysis.js`, `assets/analysis.css`, `tests/test_analysis.py`, `docs/ANALYSIS.md`, and the generated files listed above.

Replaced: `index.html`, `outlooks/index.html`, `models/index.html` (links); `.github/workflows/sunset.yml` (generation step, push path, artifacts); `scripts/package_site.py`, `scripts/package_github.py` (packaging); `README.md`, `docs/REFRESHES.md`; `output/ch-weather-github-ready.zip`, `output/ch-weather-website.zip`. Matching `_site/` preview assets are refreshed. Existing forecast calculations are unchanged. Local downloads in `.cache/analysis/` are excluded from publishing.

Upload the extracted source ZIP with folders intact, including the new `analysis/` Python files and updated workflow; keep the existing CNAME. Run the workflow once to generate these assets before deployment. No new secret is needed.

## Verification

Generated real RTMA input and 2,331 matched-age CONUS station reports. Checked all twelve map/region combinations, sparse/dense and disabled overlays, KCLT search with the original observation time/raw METAR, and composed PNG export. Mobile 390-pixel layout has no horizontal overflow; zoom/pan is available for reading detailed symbols. Automated tests cover latest-report deduplication, old/future observations, repeated cloud-layer columns, missing SLP versus a present altimeter setting, and humidity limits. All 46 tests passed.

The full GitHub source ZIP now contains more than 100 files. GitHub browser uploads may need two batches: upload the extracted folders in groups, preserving their paths, then the remaining root files. Update the existing hidden `.github/workflows/sunset.yml` through GitHub’s file editor if the upload picker hides it. Do not upload the unopened ZIP as a repository file.
