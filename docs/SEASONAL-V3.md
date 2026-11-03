# Seasonal blend version 3

## Install and run

Ubuntu / GitHub Actions (Python 3.12):

```sh
sudo apt-get update && sudo apt-get install -y libeccodes0
python -m pip install --only-binary=:all: -r requirements-sunset-dev.txt
python -m pytest -q tests/test_seasonal.py tests/test_seasonal_verification.py
MPLBACKEND=Agg python -m seasonal
python scripts/package_site.py --check --product seasonal
```

No credentials or required environment variables for the default public-data run.
`MPLBACKEND=Agg` selects headless rendering; the workflow sets it already.
Run **Seasonal climate outlooks** in GitHub Actions after uploading this update.
The existing independent publisher handles its successful artifact. Other model,
sunset, and outlook workflows do not need to be rerun for this change.
The scheduled seasonal check remains daily at 9 a.m. America/New_York; monthly
models do not acquire genuinely new forecasts every day. Cached archives limit
repeat downloads. Failures exit nonzero and leave the previous published manifest.

## What changed

- Public NMME archive search extends back to 2011 where files exist. Earlier GRIB1
  monthly intervals are decoded using their month offsets, not misleading GRIB
  validity timestamps. Missing archive years are explicitly listed.
- Temperature/precipitation stream weights and predictor variants are selected
  regionally, with regional weights shrunk toward the national fit.
- Forward test years are excluded from weight selection, feature selection,
  trend fitting, probability shrinkage, and snow conditional-strength selection.
  Earlier-year analog predictions are themselves built only from earlier targets.
- Optional predictor candidates add PDO, QBO, ENSO east/west structure, issued
  model Niño-3.4 forecasts, and a regularized temperature trend. The original
  predictors remain a competing candidate. Missing optional indices are never
  substituted with an invented neutral value. Available dimensions and historical
  sample sizes vary, so selection is not proof of a causal relationship.
- Year-balanced RMSE, climatological and raw-model comparisons, Brier scores,
  reliability bins, interval coverage, and year-block bootstrap RMSE intervals are
  saved inside each window's `verification` metadata in `latest.json`.
- Snow has a separate forward-year CRPS check. Earlier verified snow cases select
  conditional-versus-historical distribution strength. With fewer than three
  previous snow verification years, the strength is zero (historical distribution).
  The snow reference is the earlier complete-case historical distribution, not
  necessarily just 1991–2020.
- The website displays overall and regional results, mean/median differences,
  scenario ranges, and experimental chances of at least 1, 3, 6, 12, and 24 inches.
  The broad, clean contours and November–April period are retained.

## Interpret the checks correctly

Positive skill means lower error than the stated reference; negative means worse.
Temperature/precipitation skill uses squared error; snowfall uses CRPS, which
scores the whole distribution. These metrics cannot be interchanged. Spatially
correlated stations are not independent winters. The outer test-year procedure
is independent of tuning on that year, but it is not a pristine historical
reforecast experiment: model versions/membership and anomaly climatologies
changed, and fixed published 1991–2020 normals were unavailable in early years.
Sparse station support, incomplete observations, source selection, and repeated
development using this archive also limit generalization. Error intervals are
small-sample descriptive intervals, not guarantees. Do not claim validated local
snowfall accuracy or turn these experimental fractions into official warnings.

The current dynamical mean still weights six related NMME components equally;
their dependence limits the effective ensemble size. Adding their NMME aggregate
again would double count them. This update tests the combined stream against
history; it does not pretend to have member-level calibrated climate ensembles.
The percentile scenario ranges are distinct from the broad central-estimate map
bands. Snow-water-equivalent output is never converted with a fixed snow ratio.

## Additional independent climate centers: staged, not active

C3S data need a personal API token and manual, one-time acceptance of the dataset
terms: <https://cds.climate.copernicus.eu/how-to-api>.
No extra C3S models are included in the current blend. The manifest says so.
An optional staging downloader is provided, but matching hindcasts, units,
climatologies, model independence, and held-out skill must be checked before
admitting these forecasts. A download alone does not establish better accuracy.

1. Accept terms for `seasonal-monthly-single-levels` in your own CDS account.
2. Build a small CONUS request on its download page and copy the JSON selection
   from **Show API request code** into a local request file. Select a particular
   center/system, monthly lead times, years, variables, and a bounded area.
   Keep forecasts and matching-system hindcasts separately identifiable.
3. `python -m pip install -r requirements-seasonal-external.txt`
4. Set `CDSAPI_KEY` only in your environment or a GitHub Actions secret; this is
   the only required variable for the optional downloader. Never commit the token.
5. `python -m seasonal.download_c3s --request request.json --output .cache/c3s/monthly.grib`

The default Actions job does not use this token or request C3S data. Do not add a
secret and assume it automatically activates another model. C3S queue delays and
large hindcasts are deliberately outside the unattended daily production path.
The downloader exits nonzero on failed/empty downloads, stages a temporary file,
and only replaces its target after success. Server-side queue time is controlled
by the external service; run staging downloads in a separately timed job.

## Files added or changed for version 3

Core: `seasonal/data.py`, `seasonal/blend.py`, `seasonal/verification.py` (new),
`seasonal/__main__.py`, `seasonal/download_c3s.py` (new).

Website: `seasonal/index.html`, `assets/seasonal.js`, `assets/seasonal.css`.

Setup/tests: `.github/workflows/seasonal.yml`, `scripts/package_github.py`,
`tests/test_seasonal_verification.py` (new), `requirements-seasonal-external.txt`
(new), `docs/SEASONAL.md`, this guide (new).

The update ZIP also includes the earlier seasonal integration files, so it works
when upgrading from an older local copy. Generated seasonal PNG/JSON assets are
rebuilt by the workflow rather than included in the source upload ZIP.
