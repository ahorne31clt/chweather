# CH Weather Blend / seasonal outlooks — version 2

## What changed

The default `/seasonal/` view is now a distinct experimental CH Weather Blend. It combines all six current NMME component models with observed-state statistical guidance. NMME itself remains a comparison and is not counted as an additional model. The page provides temperature, precipitation and snowfall anomalies; above/below-average maps for those variables; and an expected seasonal snowfall amount map in broad bands: 0–3, 3–6, 6–12, 12–24, 24–36, 36–60, 60–90, 90–120, 120–180 and 180+ inches.

The snowfall amount bands classify a central seasonal estimate. They are NOT storm totals or confidence intervals. The city selector shows the wider historical 10th–90th percentile scenario range. Neither snow probabilities nor the scenario range have independently verified forecast coverage.

## Smoother maps and CONUS coverage

The original 90-city network is supplemented by a spatially distributed selection of NOAA USHCN cooperative stations retrieved through ACIS. The tested source network contains 760 records. Each field only uses records meeting its own completeness requirements, so this does not mean 760 independent contributing stations on every map. The model/state blend presently has about 134–144 usable temperature/precipitation records and 98–109 joint snowfall records per window; the pure analog field can use a different sample.

Station contours use non-overshooting linear interpolation inside the observation convex hull and inverse-distance edge extension outside it, followed by broad regional Gaussian smoothing (approximately 120 km standard deviation on the display grid). Simpler contour bands emphasize seasonal regions rather than small isolated peaks. The display grid is 0.2°, not a claim of 0.2° predictive resolution. A metadata coverage fraction records edge extrapolation or a nearest-record distance over approximately 180 km. Maps use clean contour fills without hatching or gray coverage overlays. CONUS land is filled, including low-snow climates with measured zero totals. Missing observations are never replaced with zero; unsupported areas are extensions from nearby data and remain documented in the coverage metadata. High-elevation, coastal and lake-effect details are not resolved reliably.

Snowfall amount and anomaly surfaces use an additional, much denser NOAA NCEI 1991–2020 published snowfall-normal network. We interpolate log1p seasonal normals, then apply a smooth relative blend/analog departure factor instead of spreading an absolute mountain snowfall amount across deserts or coasts. Published zero-normal cells retain a zero central estimate (not a guarantee of no storm snow). The official by-variable monthly table uses customary inches, requires at least ten contributing years for accepted entries, and retains the publisher’s normal-estimation methods. This interpolated surface is not an official NOAA gridded snowfall product. Station city readouts use their own complete-case reference and can differ from the denser mapped normal surface.

## Sources and the blend recipe

Dynamical components, each entered once at equal weight within one model stream:
- NOAA CFSv2 Monthly
- ECCC CanESM5
- ECCC GEM5.2-NEMO
- NASA GEOS-S2S
- NCAR CCSM4
- NCAR CESM1

This covers the six current public NMME components, not literally every global climate model. No ECMWF/C3S subscription, account or unavailable data is claimed. The published NMME aggregate and adjusted tercile probabilities remain separate comparison views. CFSv2 Monthly is the monthly initialization in NOAA’s NMME archive, not the separate daily rolling CFS ensemble.

Model and historical data:
- https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom/ENSMEAN/
- https://ftp.cpc.ncep.noaa.gov/NMME/prob/netcdf/
- https://www.cpc.ncep.noaa.gov/products/NMME/data.html
- https://www.cpc.ncep.noaa.gov/products/NMME/about.html
- https://www.ncei.noaa.gov/pub/data/ushcn/v2.5/ushcn-v2.5-stations.txt
- https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/archive/us-climate-normals_1991-2020_v1.0.1_monthly_precipitation_by-variable_c20230404.tar.gz
- https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/doc/inventory_30yr.txt
- https://data.rcc-acis.org/MultiStnData
- https://docs.rcc-acis.org/acisws/
- https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt

Observed atmospheric inputs:
- https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/monthly.ao.index.b50.current.ascii
- https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.nao.monthly.b5001.current.ascii
- https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.pna.monthly.b5001.current.ascii

The statistical stream matches same-calendar historical seasons using observed ONI level and its three-month tendency, observed AO/NAO/PNA, and preceding three-month local temperature/precipitation departures. A nearest-analog weighting of standardized feature distance selects 15 historical candidates. AO/NAO/PNA distance contributions decrease exponentially with lead; their current sign is not forecast to persist for a season. Where recent observations at an old station are missing, nearby active records provide a regional standardized recent-condition anomaly; this is flagged in station metadata.

The two stream weights are estimated per season and variable using archived monthly NMME forecasts beginning in 2018. Each statistical development prediction uses earlier observed seasons, and the model side uses the issued archived anomaly directly. No short-archive station bias offset is added to already-referenced model anomalies. We minimize normalized squared error over forward-held-out cases on a 0.05 weight grid with a small penalty toward an even stream mixture. Thus all variables/seasons need not receive the same weight, and a stream can receive zero weight if development cases favor the other. Current weights, source months and development case counts appear on the page and in latest.json.

This is a development fit, NOT an independent skill verification or proof of calibrated probabilities. The cases used to choose weights cannot then provide an independent accuracy claim. Stations are spatially correlated, the archive is short, model membership and climatologies evolved, and the historical NMME aggregate is a development proxy for the modern six-component mean. No station-specific anomaly offset is applied; the stream mixture uses the model and statistical anomalies directly. The page and JSON disclose these limits.

Temperature/precipitation outcome distributions use the blended mean and centered, scaled forward-held-out residuals, with 20% climatological mass in above/below estimates to limit small-sample confidence. Snow uses measured historical snowfall from seasons with complete joint temperature, precipitation and snowfall records. We condition that distribution on the blended seasonal temperature/precipitation pattern and observed-state similarity, with 20% climatological shrinkage. There is no temperature-to-snow ratio or invented snowfall model output. Broad amount bands classify the conditional mean; the historical 10th–90th percentile scenario range is reported separately. Ties at the average (especially zero snow) are retained, so above and below fractions need not sum to 100%.

At least 24 complete normal seasons in 1991–2020 are required. Pure ENSO composites additionally need eight matching seasons; the blend statistical sample needs at least 30 historical feature/target cases, and joint snow needs 24 usable cases. Missing months are never silently filled. Trace precipitation/snow is zero measurable accumulation. The normal period uses the center-month convention: DJF 1991 = December 1990–February 1991. Historical station records retain their climate background and relocations; no independent homogenization is claimed.

Monthly temperature anomalies are day-weighted and converted from K departures to °F (multiply by 1.8; no +32 offset). Monthly precipitation rates are unit-checked, converted from mm/s when necessary, integrated over actual calendar days and converted to inches. Published NMME seasonal probabilities are read directly, never averaged from monthly probabilities. CPC files currently label percent while encoding fractions; the three-category simplex must sum to either 1 or 100 before conversion. NMME categories are terciles; blend probabilities instead compare with the arithmetic station average.

## Run unattended

Python 3.12, repository root, Ubuntu:

```sh
sudo apt-get update
sudo apt-get install -y libeccodes0
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements-sunset.txt
python -m seasonal
```

Windows with the existing environment: `.venv/Scripts/python.exe -m seasonal`.

No dependencies were added. The single command fetches public data, calculates all views, and renders the finished maps. No desktop, prompt, manual login or API key is used. It writes generated/seasonal/latest.json, map PNGs, and shared station-value JSONs. Failed generation exits nonzero; no illustrative data is substituted and the new manifest is committed last. Source download sizes are bounded and files older than 100 days are pruned. Observation requests are batched and cached; initial source retrieval can be much slower than subsequent cached runs. Forecast fields themselves update monthly, not daily.

Required generation environment variables: **none**. Optional runtime settings already supplied by the workflow: MPLBACKEND=Agg, TZ=UTC, PYTHONUNBUFFERED=1, OMP_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1. The publisher requires GH_TOKEN and GITHUB_REPOSITORY, automatically provided by GitHub Actions; never embed credentials in source.

## Upload and workflows

1. Extract output/ch-weather-blend-update.zip and upload its folders to the repository, preserving paths. Do not upload the ZIP itself or delete the rest of the site.
2. Replace .github/workflows/seasonal.yml and .github/workflows/publish.yml from the update. If .github is hidden, use GitHub Add file > Create new file, type the exact path, and paste from the visible output/seasonal.yml and output/publish.yml copies.
3. Run Actions > Seasonal climate outlooks > Run workflow.
4. Publication follows automatically. If necessary, manually run Publish latest weather website after the seasonal artifact exists.

The seasonal workflow is independent of the larger weather-model jobs. It checks daily at 9 AM America/New_York, retains its artifact for 35 days, and triggers the publisher. Its first uncached run has a 60-minute generation allowance within a 90-minute job; subsequent runs reuse source caches. A failure does not block other product workflows. The publisher retains the most recent valid seasonal artifact with its original timestamps, or explicitly reports unavailability when none exists.

## Files in this update

Seasonal calculation/UI:
- seasonal/__init__.py
- seasonal/data.py
- seasonal/science.py
- seasonal/render.py
- seasonal/blend.py (new)
- seasonal/__main__.py
- seasonal/index.html
- assets/seasonal.css
- assets/seasonal.js

Integration/setup (included so this ZIP also works when version 1 has not yet been uploaded):
- assets/navigation.js
- enso/index.html
- scripts/package_site.py
- scripts/package_github.py
- tests/test_packaging.py
- tests/test_seasonal.py
- .github/workflows/seasonal.yml
- .github/workflows/publish.yml
- docs/SEASONAL.md
- README.md

Generated maps and shared JSON files are included in portable website exports and created by Actions; they do not need manual source uploads. No change to sunset.yml or models.yml is needed.

## Sign and contour corrections

The initial development version incorrectly allowed a short-archive bias offset and the nonzero mean of development residuals to shift the published mean a second time. These were removed: temperature anomalies now remain the convex weighted mean of the raw model and statistical anomalies, and uncertainty residuals are centered to zero. Station readouts expose both contributions, their weights and the zero added offset. A regression test checks this identity and checks that unobserved target months cannot influence the forecast. Clean fills replace every coverage hatch/gray overlay. Regional smoothing and wider temperature bands reduce isolated interpolation hotspots.


## Full November–April snowfall outlook

Use the **November–April snowfall outlook** button or choose the FULL SNOW SEASON entry in Forecast period. This view has five maps: total seasonal snowfall (central estimate in inches), snowfall anomaly, chance above the six-month average, chance below the six-month average, and expected snowfall range. Total and range views show the same central forecast with different legends, not independent predictions.

The six-month blend is calculated directly from November, December, January, February, March and April. It does not sum overlapping three-month outlooks or average their probabilities. Model temperature is day-weighted across all six months, precipitation departures are integrated over all six months, and historical snow totals, reference periods, conditional distributions and above/below fractions are computed over that same six-month period. Full-season station normals use winter ending years 1991–2020. The separate NOAA normal surface sums its six calendar-month normals.

If part of the period precedes the selected model initialization, complete observed monthly climate departures replace those missing model months. Observed snowfall already accrued is retained and historical remaining-season scenarios are added to it; they cannot erase measured snow. Missing observed months are not filled with zero. The full-season option is published only when source data reach April. No forecast beyond the available model horizon is invented.

Full-season artifacts use a separate period identifier (`snow-season-YYYY`) and `-full` filenames so they cannot be confused with November–January maps starting on the same date. This update changes seasonal/science.py, seasonal/blend.py, seasonal/__main__.py, seasonal/render.py, seasonal/index.html, assets/seasonal.js, tests/test_seasonal.py and this guide. The same independent seasonal workflow builds and publishes these maps; no workflow changes are required for this addition.

## Version 3

The current year-blocked verification, additional predictor candidates, snowfall scoring, optional C3S staging, setup and changed-file list are documented in [SEASONAL-V3.md](SEASONAL-V3.md). Earlier version 2 development notes above describe the prior implementation.

