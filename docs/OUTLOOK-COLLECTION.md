# CH Weather outlook collection

Open `/outlooks/collection.html`. Eight outlooks each have a CONUS and North Carolina graphic: daily weather with WPC fronts, outdoor weather, stargazing, frost/freeze, snowfall, flat-ice accumulation, comfortable weather, and temperature forecast confidence. Existing page paths are unchanged. Main-site dropdowns link to existing tools and these new views; the portfolio keeps its separate navigation.

## Data and meaning

The weather source is NOAA/NCEP's National Blend of Models, native spacing approximately 2.54 km. Public S3 index and exact byte-range downloads fetch individual GRIB2 records, not full model files. Requests verify run, lead, parameter, vertical level, grid consistency, accumulation interval, physical units, and percentile/precipitation thresholds. A cached all-eight run used about 96 MB of source files; the 16 finished PNGs occupy about 6 MB. No API keys are required.

NBM core records can use **alternating east/west row scanning** (scan mode 80), while percentile records can use ordinary rows (64). The reader reverses odd stored rows where required before spatial sampling. This corrects the curved striping seen in the first comfort/outdoor preview; it is a decoding correction, not cosmetic smoothing. Confidence fields retain their normal ordering. Tests cover both modes.

The forecast window is the next UTC calendar day, 00–00 UTC. Local calendar dates differ, particularly for the overnight products. The generator selects the latest available 00/12 UTC NBM cycle with a four-hour availability allowance, falling back to two earlier cycles only if required inputs are incomplete. National graphics sample at 0.15°; North Carolina at 0.025°, using the nearest native point. Three-hourly samples are used for time-based indices. No resampling is claimed to create more model resolution.

| Outlook | Calculation and limitations |
| --- | --- |
| Daily weather | Maximum sampled 3-hourly 2 m temperature in the 24-hour window. Rain hatching means at least one 6-hour interval has ≥50% probability of >0.01 inch liquid-equivalent precipitation; it is not a 24-hour PoP. |
| WPC fronts | Official front and H/L coordinates from the WPC National Forecast Chart are redrawn with standard symbols. The separate front valid time is printed and preserved. No fronts are diagnosed from temperature or pressure thresholds. No pressure-center values are invented. |
| Outdoor weather | Mean daytime score where approximate solar altitude exceeds 5°. Start with 100; penalize temperatures below 50°F (1.7/degree) or above 82°F (2.2/degree), RH above 65% (0.25/point), winds above 10 mph (2/point), gusts above 20 mph (2/point), and the matching 6-hour precipitation probability (0.8/point). Clip to 0–100. Not a safety or lightning assessment. |
| Comfortable weather | Mean daytime score: 100 minus 2.5/degree below 60°F, 3/degree above 78°F, 0.5/RH point above 60%, 3/mph above 8 mph, and 0.8/point of matching 6-hour precipitation probability. Clip 0–100. A subjective preference index, not a health index. |
| Stargazing | Mean nighttime score where Sun is below −18°: 100 minus total cloud percentage, 0.3/RH point above 85%, and 2/mph above 10 mph; clip 0–100. Moon illumination is computed separately with Astronomy Engine 2.1.19. No moonrise, seeing, smoke, or local light-pollution prediction is claimed. |
| Frost/freeze | Highest category among 3-hourly nighttime samples: ≤28°F hard-freeze temperature guidance; >28–32°F freeze; >32–36°F frost-favorable if RH≥80%, clouds≤30%, wind≤5 mph. These are screen-level temperatures, not leaf or pavement temperatures. Brief lows between samples can be missed; no crop-damage or duration guarantee. |
| Snowfall | Sum four consecutive non-overlapping 6-hour deterministic ASNOW accumulations. Source is snowfall depth in meters, converted to inches. Not snow-cover depth; no arbitrary snow-to-liquid ratio. Not an official NWS snowfall forecast. |
| Ice | Sum four consecutive 6-hour NBM FICEAC (FRAM flat ice) accumulations. Source kg/m² is converted using the conventional mm equivalent and divided by 25.4 for inches. Not radial ice on power lines, road icing, or outage prediction. |
| Temperature confidence | NBM 90th minus 10th percentile 2 m temperature at the middle of the window, displayed as an °F range. Narrower means greater temperature agreement. It is not a percentage accuracy score or confidence in precipitation/severe weather. No percentiles are added across time. |

All methods, source URLs, actual model runs, generation timestamps, valid windows, image filenames, and SHA-256 hashes appear in each `latest.json`. Indices are explicitly experimental CH Weather products, not calibrated probabilities. Official warnings remain linked separately.

Sources: [NBM](https://vlab.noaa.gov/web/mdl/nbm), [NCEP moisture parameter units](https://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_table4-2-0-1.shtml), [WPC forecast chart](https://www.wpc.ncep.noaa.gov/NationalForecastChart/map.php), [Astronomy Engine](https://github.com/cosinekitty/astronomy).

## Commands and outputs

Install dependencies with `python -m pip install -r requirements-sunset.txt`. Astronomy Engine is a small pure-Python wheel; no desktop application, separate ephemeris download, manual login, or Node build is needed.

```
python -m specialty --product all
python -m specialty --product comfort
python -m scripts.run_product specialty-daily
```

Product arguments: `daily`, `outdoor`, `stargazing`, `frost`, `snow`, `ice`, `comfort`, `confidence`. For each product, output is `generated/specialty-PRODUCT/latest.json`, `PRODUCT-national.png`, and `PRODUCT-nc.png`. One command downloads inputs, computes, renders, and writes the finished outputs. Failures exit nonzero, preserve the previous successful manifest, and do not substitute illustrative data.

## GitHub upload and automatic updates

1. Extract `output/ch-weather-outlook-collection-update.zip`; upload its **contents**, preserving folders and replacing matching paths. No pages need to be deleted or renamed.
2. Replace `.github/workflows/sunset.yml` with the updated `output/sunset.yml`. It now includes an independent job for each of the eight new outlooks, using the generic product runner. Existing model scheduling is unchanged. Upload the Python modules, requirements, and publishing/package scripts too; changing the workflow alone is insufficient.
3. Keep Pages source set to GitHub Actions. Start a fresh **Daily weather and sunset outlooks** run on `main`. The separate publisher collects successful individual artifacts and deploys the site. Old runs use old code; start a fresh run.

The existing schedule applies: 8 a.m. America/New_York, plus 05:30 / 11:30 / 17:30 / 23:30 UTC. Each new outlook gets its own job. One failed outlook does not block its successful peers; the publisher can retain previous valid artifacts with original dates, or show a product as unavailable if none exists. User-configured credentials are not needed. `GH_TOKEN` and `GITHUB_REPOSITORY` remain automatically supplied by the publisher; `MPLBACKEND`, thread limits, and UTC settings remain supplied by the workflows.

## Changed files

Added: `specialty/__init__.py`, `specialty/config.py`, `specialty/data.py`, `specialty/science.py`, `specialty/render.py`, `specialty/__main__.py`; `scripts/run_product.py`; `outlooks/collection.html`; `assets/collection.css`, `assets/collection.js`, `assets/navigation.css`, `assets/navigation.js`; `tests/test_specialty.py`; this guide.

Updated: `.github/workflows/sunset.yml`, `requirements-sunset.txt`, `scripts/package_site.py`, `scripts/collect_publication.py`, `scripts/package_github.py`; `index.html`, `sunset/index.html`, `outlooks/index.html`, `outlooks/centers.html`, `tropical/index.html`, `alerts/index.html`, `mos/index.html`, `enso/index.html`; `README.md`.

Generated: all eight `generated/specialty-*/` directories (16 maps and eight manifests), the local `_site/` preview, complete source/static ZIPs and the small collection update ZIP in `output/`. Caches are development artifacts and are excluded from exports. The update ZIP includes the matching publication/test support files so the independent product pipeline remains consistent.
