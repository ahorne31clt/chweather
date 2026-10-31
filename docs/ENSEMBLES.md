# REFS and GEFS ensemble probabilities

Open `/ensembles/` or use the Ensembles link in the model room. Generate with:

```bash
python -m ensembles
```

Uses existing `requirements-sunset.txt` dependencies and Ubuntu installation from `docs/SUNSET.md`. No required environment variables, API keys, desktop windows or manual login. The updated 8 a.m. America/New_York workflow runs this command with a 12-minute step timeout before model/export/deploy steps. The default forecast is the most recent eligible 00/06/12/18 UTC cycle, allowing five hours for publication and trying at most two preceding cycles. Probe the final published hour first. All fields/members in each model's published sequence use a single cycle. Models may have different actual selected cycles, always identified. Any incomplete intermediate frame fails the publication rather than silently changing run, denominator or horizon.

## GEFS

Real NOAA public GEFS `pgrb2ap5` 0.5° atmospheric records, one control c00 and all perturbed members p01–p30. Use F024 through F384 at 24-hour display steps. Each member's GRIB initialization, forecast lead, perturbation number, field, units, accumulation interval and grid are checked. All 31 members must be present, finite and on the same grid. Raw, uncalibrated probability is `100 × count(member meets threshold) / 31`. Missing members never reduce the denominator. No Gaussian assumption, spread-to-probability conversion or deterministic stand-in.

Products:
- Instantaneous 2 m temperature strictly below 32°F.
- Instantaneous 2 m temperature strictly above 90°F.
- Six-hour liquid-equivalent precipitation at least 0.10, 0.50 or 1.00 inch.

GEFS precipitation records must have `startStep = forecast_hour - 6` and `endStep = forecast_hour`. Consequently the maps cover six-hour windows sampled once per day. They do **not** cover the intervening 18 hours, a 24-hour probability or cumulative precipitation from initialization. Exact interval start/end stays visible. The published 0.5° product is the source resolution; no 3-km GEFS detail is invented.

## REFS

Real NOAA operational RRFS/REFS public `refs.YYYYMMDD/HH/ensprod/refs.tHHz.prob.fFF.conus.grib2` probability records on the native 3-km grid. Published every six forecast hours from F006 through F060. Preserve NOAA's probability field instead of inventing individual members or converting a mean/spread to probability.

Products:
- Pointwise probability of 2 m temperature strictly below 32°F.
- Pointwise probability of lowest-90-mb mixed-layer CAPE strictly above 1000 J/kg.
- NOAA neighborhood probability of six-hour precipitation strictly greater than 1.00 inch.

Validate the GRIB probability type, scaled physical threshold, level/variable selection, units, run, lead, accumulation interval, grid and 0–100 output range. NOAA's contributor count is read from its probability header (`totalNumberOfForecastProbabilities`, reflected in the index's `prob fcst 0/N`) for every frame and must agree between selected fields. The count can decrease at long leads; the actual first generation showed 14 contributors at earlier times and 6 at F060. Do not assume a constant REFS denominator or claim a neighborhood percentage is a direct pointwise member count.

NOAA's neighborhood rainfall processing is preserved; it is not an address-level rain chance. The neighborhood radius is not inferred from the probability GRIB or invented in the interface. Users are referred to the official product documentation for the publisher's spatial-processing definition. CAPE probability is not a tornado/severe-storm probability. All precipitation is liquid-equivalent, including frozen precipitation's water content.

## Interface and outputs

Map-first viewer with model/threshold selectors, timeline, previous/next/play, keyboard arrows/Space, PNG links, shareable model/product/hour URLs and source guide. Model switching preserves the closest published UTC valid time and reports when an exact match is unavailable. Run, valid interval, point/neighborhood type and per-frame contributor count remain visible. Runs older than 24 hours are labeled. Refresh checks published files; generation/deployment determines when a newer cycle appears. A failed image hides the graphic, and a failed publication never fabricates a zero-probability map.

Cursor/tap probabilities come from a nearest-native numerical lookup sampled every five image pixels, rounded to 0.1 percentage point. This display lookup is not added meteorological resolution. A SHA-256-verified gzip little-endian uint16 payload stores probability × 10; 65535 means missing/outside map. Categorical color bins are only presentation. The underlying NOAA probability values/member fractions are not modified to match the color bins.

Outputs: `generated/ensembles/latest.json`, 110 map PNGs (30 REFS, 80 GEFS), and matching small `.bin.gz` cursor lookups. Cycle-specific filenames prevent a cached old manifest from loading a new run under the same image path. Each 2000 × 1125 graphic retains a source/run/validity label, member count and percentage legend. Manifest includes initialization, generation UTC, exact per-product validity, contributor count, GEFS member IDs, source URLs and asset hashes. These are not official NWS warnings or calibrated point forecasts.

## Resources and failure behavior

Only exact indexed GRIB byte ranges are fetched, capped at 5 MB each. Require HTTP 206, a matching Content-Range, exact length and GRIB framing; full-file substitutes are rejected. At most four GEFS member downloads overlap, with ecCodes access serialized for portability. Each request has bounded retries/timeouts. Fields are cropped to CONUS before stacking the GEFS members, keeping memory small. Only one frame is processed/rendered at a time. Cached records are never published as website assets. No full global GRIB files or complete REFS probability bundles are downloaded. All images/metadata are staged and the manifest published last. A failed hosted generation prevents deployment and leaves the previous successful Pages site available. A process crash between final local renames can interrupt local publication, as with the other static generators.

Sources: [NOAA REFS inventory](https://www.nco.ncep.noaa.gov/pmb/products/refs/), [REFS probability-field inventory](https://www.nco.ncep.noaa.gov/pmb/products/refs/refs.t06z.prob.f32.conus.grib2.shtml), [NOAA GEFS inventory](https://www.nco.ncep.noaa.gov/pmb/products/gens/), NOAA public `noaa-rrfs-ops-pds` and `noaa-gefs-pds` S3 archives, Natural Earth boundaries.

## Exact files added or replaced

Added: `ensembles/__init__.py`, `ensembles/data.py`, `ensembles/render.py`, `ensembles/__main__.py`, `ensembles/index.html`, `assets/ensembles.js`, `assets/ensembles.css`, `tests/test_ensembles.py`, `docs/ENSEMBLES.md`, and the generated outputs described above.

Replaced: `index.html`, `outlooks/index.html`, `models/index.html` (links); `.github/workflows/sunset.yml` (generation, push path, artifact); `scripts/package_site.py`, `scripts/package_github.py` (packaging); `README.md`, `docs/REFRESHES.md`; `output/ch-weather-github-ready.zip`, `output/ch-weather-website.zip`. Matching `_site/` preview assets are refreshed. Existing deterministic-model and sunset calculations are unchanged.

Upload extracted source contents with folders preserved, including the new `ensembles/` Python package and matching workflow. Keep the existing CNAME. No new secret. The source ZIP excludes generated forecasts; Actions builds them. GitHub browser uploads may need multiple batches because the complete source package exceeds 100 files.

## Verification

Generated all 110 real-data maps and numeric lookup files. Confirmed REFS F060 uses the source-reported six contributors and GEFS F384 uses all 31 members. Checked all product controls, six-hour interval labels, model switching, playback/wraparound, cursor percentages, mobile layout and original PNG links. Tests verify strict threshold comparisons, complete finite denominators, unique index selection, bounded byte ranges, recent cycle selection, and preservation of the previous publication when the second ensemble is incomplete after the first was already staged.
