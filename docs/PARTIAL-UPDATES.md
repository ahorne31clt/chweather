# NDFD timing repair and independent failure handling

## What failed

At 18:19 UTC on October 31, the NOAA maximum-temperature file was already available with an 18:30 UTC GRIB production reference. The old code treated that nominal cycle time as a publication timestamp and rejected anything over ten minutes ahead. The repaired code allows one 30-minute production slot while keeping the 24-hour stale limit and the existing checks on forecast validity, units, coverage, and temperature/PoP period matching. Labels now say **NDFD production reference**, retaining the actual source timestamp rather than changing it to the current time.

NOAA documents the GRIB reference time as the NDFD production cycle: https://graphical.weather.gov/docs/grib_design.html . The change was checked against a real NOAA download, and a fresh `python -m weather` successfully rendered all nine products.

## If one product fails

- Matrix jobs keep `fail-fast: false`: a weather failure does not cancel sunset, tropical, centers, ENSO, RTMA, ensembles, or the other models.
- Each generation step retains its nonzero exit status on failure. Its later validation/upload steps still run when valid partial output exists. Invalid or missing output is not uploaded.
- The weather generator saves successfully rendered SPC/foliage products even if NDFD fails, and still reports a failed/partial generation step. A source failure is not disguised as success.
- Publication runs after a generation workflow completes, including failures or timeouts. It retrieves **each product's newest validated artifact**, rather than requiring the whole workflow or a combined bundle to succeed.
- Previous successful artifacts remain usable for three days with their original issue, valid, and generation timestamps. Missing weather-map types can be filled from earlier successful weather artifacts without overwriting current SPC maps. The page labels these retained graphics.
- GFS, HRRR, and NAM are recovered independently. An HRRR failure does not prevent a good GFS or NAM run from publishing. Missing models are explicitly unavailable. Airport catalogs are not mixed: an incompatible airport dataset is omitted while the valid model maps remain available.
- With no previous successful data for one product, it is explicitly unavailable; the rest can publish. If no validated artifacts exist at all, publication fails and the existing website remains deployed.

The generator may therefore show a red failed step while successful products still reach the site. Check the separate **Publish latest weather website** run for deployment status. Nothing fabricates missing data or changes old forecast dates to today's date.

## Apply this update

1. Extract `output/ch-weather-reliable-updates.zip`. Upload its folder contents to the repository root, preserving the `weather/`, `scripts/`, `assets/`, `models/`, `tests/`, and `docs/` paths and replacing matching files.
2. Replace all three files inside `.github/workflows/`: `sunset.yml`, `models.yml`, and `publish.yml`. Updated visible copies are supplied at `output/sunset.yml`, `output/models.yml`, and `output/publish.yml`. The upload-on-partial-failure logic requires these new versions.
3. Commit to `main` and start fresh runs of **Daily weather and sunset outlooks** and **Scheduled weather models** if they do not start from the commit. Their completion triggers publication automatically. Do not rerun an older commit.

Folder placement matters: `scripts/collect_publication.py` must replace that path, not create `collect_publication.py` at repository root. The same applies to `weather/sources.py` and the files inside `tests/`.

## Files in the update

- Workflows: `.github/workflows/sunset.yml`, `models.yml`, `publish.yml`.
- Weather source/rendering: `weather/sources.py`, `weather/__main__.py`, `weather/render.py`.
- Publication: `scripts/collect_publication.py`, `scripts/merge_models.py`, `scripts/package_site.py`, `scripts/package_github.py`.
- Browser labels: `assets/outlooks.js`, `assets/models.js`.
- Supporting model selection: `models/__main__.py`.
- Tests: `tests/test_weather.py`, `tests/test_independent_publication.py`, `tests/test_packaging.py`, `tests/test_model_selection.py`.
- Documentation: `README.md`, `docs/REFRESHES.md`, `docs/MODELS.md`, `docs/FIX-AUTOMATIC-UPDATES.md`, this document.

No new user-configured credentials or environment variables. `GH_TOKEN` and `GITHUB_REPOSITORY` are supplied automatically by the publication workflow; existing headless-rendering variables remain unchanged.
