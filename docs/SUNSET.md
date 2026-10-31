# CH Weather daily sunset outlook

This is an experimental, physically informed **heuristic**, not a trained model,
validated probability, official NWS forecast, or an SPC product. It consumes real
NOAA numerical forecast guidance; no illustrative forecast values are substituted.

## Install and run on Ubuntu

Python 3.12 and Ubuntu 24.04 are used in GitHub Actions. From this repository:

```bash
sudo apt-get update
sudo apt-get install -y python3-venv libeccodes0
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-sunset.txt
python -m sunset
```

After installation, the **single command** `python -m sunset` fetches the data,
calculates the outlook, downloads map boundaries if needed, and renders both:

- `generated/sunset/latest.png` (2400 × 1500 PNG)
- `generated/sunset/latest.json` (run, valid date, generation UTC, image filename,
  SHA-256, source download URLs, algorithm version, three locations and limitations)

Run from the repository root. Paths default to the repository root even if the
working directory differs, provided the package is on Python's import path.
No browser, desktop, interactive prompt, notebook, GPU, manual authentication,
paid API, account, or weather API key is used. Matplotlib's `Agg` backend is selected
in code. The existing logo is included without changing its pixels or proportions.

Useful optional arguments:

```bash
python -m sunset --date 2026-10-30 --run 2026103000
python -m sunset --cache-dir .cache/sunset --output-dir generated/sunset
python -m pip install -r requirements-sunset-dev.txt
python -m pytest -q tests/test_sunset.py
```

`--date` is the evening's calendar date at each location, not the UTC sunset date.
The default date is today in **America/New_York**. UTC sunset hours can exceed 24
in the western US. `--run` must be an available extended HRRR cycle (00/06/12/18 UTC), at most 24 hours old,
not in the future, with supported forecast leads. This command is not an archive
backfill tool; NOMADS only retains recent data. A historical example eventually
expires. Never change the date label without downloading data valid for it.

## Environment variables and credentials

**Required environment variables for the command: none.** No credentials are
needed for NOAA/NOMADS or Natural Earth. Optional standard library variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY` | Optional Requests/network proxy configuration | System/Requests defaults |
| `REQUESTS_CA_BUNDLE` | Optional custom CA bundle for Requests | Default trusted CA bundle |
| `MPLCONFIGDIR` | Optional writable Matplotlib font/config cache | Matplotlib's normal user cache |

No custom pipeline environment variables are required. CLI arguments configure
date, cycle, cache, and output locations. Do not disable TLS verification.

GitHub Actions automatically provides `GITHUB_TOKEN` and ephemeral OIDC values
to the official Pages actions. No user-managed secret or personal access token
is required. The workflow grants `contents: read`, `pages: write`, and
`id-token: write`. If you later use another host, keep its credentials in GitHub
Actions Secrets and pass them as environment variables in that host's deployment
step; there are no such credentials in this implementation.

## Activate daily website publication

1. Put these files in a GitHub repository and push to its default branch. There
   is currently no configured Git remote in this workspace; this has **not** been
   uploaded, scheduled remotely, or deployed by this chat.
2. In the repository's **Settings → Pages → Build and deployment**, choose
   **GitHub Actions** as the source. Allow Actions and the workflow's Pages/OIDC
   permissions. For a protected `github-pages` environment, allow deployment
   from the default branch without a required human approval if unattended
   publication is desired. GitHub Pages availability depends on your plan and
   repository visibility.
3. `.github/workflows/sunset.yml` runs automatically on its daily schedule and
   also supports an initial **Actions → Daily sunset outlook → Run workflow**.
   Relevant pushes to `main` also trigger it. If your default branch has another
   name, update the `push.branches` entry; the schedule uses the default branch.
4. It installs dependencies, runs tests, generates the graphic, exports the
   allowlisted static website, and deploys the complete site and new forecast
   together using the official GitHub Pages actions. No bot commit is needed.
5. Later, connect `chweather.com` through Pages and your DNS provider. Paths are
   relative so a repository Pages URL works too. For another hosting service,
   publish the `_site/` export from the same successful job instead of Pages.

The schedule is `0 8 * * *` with `timezone: America/New_York`, so GitHub handles
EST/EDT. **8 a.m. is the scheduled start, not a guaranteed publication time.**
GitHub may queue or delay runs, and data/rendering/deployment take additional
time. If precise 08:00 delivery becomes a hard requirement, use infrastructure
with a timing SLA or precompute before release. No unattended host can promise
fresh outputs during upstream or hosting failures. GitHub can automatically
disable schedules on inactive public repositories after 60 days; check Actions
if updates stop. The job has a 20-minute timeout and does not silently continue
after failed tests, downloads, processing, or rendering.

## Meteorological method, version ch-sunset-2.0.0

### Input and spatial/temporal treatment

- NOAA/NCEP **HRRR 3 km** instantaneous `LCDC`, `MCDC`, `HCDC` cloud cover (%) and surface `VIS` (m), from the public NOMADS HRRR 2-D filter. The complete native Lambert grid is retained; no coarse GFS input or REFS ensemble is substituted.
- Score native grid points within 24–50°N, 125–66°W, masked to contiguous US land using Natural Earth 1:50m boundaries. The PNG is 2400 × 1500; physical inputs remain 3 km.
- Only extended 00/06/12/18 UTC cycles are eligible, with a three-hour publication allowance and at most two preceding-cycle attempts. At 8 a.m. Eastern the 06 UTC cycle is normally selected. Never use an ordinary 18-hour cycle.
- Compute the minimum/maximum sunset time over the CONUS bounding box, including sunsets on the following UTC day. Require all hourly steps bracketing those times to fall within forecast hours 0–48. Check the farthest required step first. Download only that short hourly window, not all 49 steps. A run that stops before sunset is rejected; there is no GFS fallback or extrapolation.
- Use NOAA approximate solar timing with a 90.833° zenith, flat horizon and standard refraction. Interpolate hourly forecasts linearly in time and bilinearly in native projected coordinates at each location's sunset.
- Sample sunward low/mid cloud at 80, 160, and 240 km along the seasonal solar azimuth at the observer's sunset time. Out-of-domain rays have no score; require at least 99% CONUS land coverage before publishing and report the actual fraction. The first HRRR run covered 100%.
- Validate grid spacing, levels, units, initialization, forecast lead, missing values and cloud bounds for every field and hour. Never mix runs or averaged and instantaneous cloud records.
- Evaluate in 40,000-point chunks with float32 input cubes to keep memory modest on an Ubuntu runner. Smooth only 0.65 native cells, with a mask-normalized kernel that cannot spread missing values into the land scores.
- Location search uses nearest native scores on a 0.03° geographic lookup lattice. `lookup.json` describes `lookup.bin.gz`: two little-endian signed-int16 planes (score × 10, UTC sunset minutes), missing value -32768. The browser checks the compressed payload SHA-256 and decompresses locally. This lattice does not add physical detail to HRRR.

### Exact score

Cloud cover is converted to fractions `L` (low), `M` (middle), `H` (high).
`clip(x)` means constrain to 0–1. `V` is visibility in meters.

```text
U = max(0.9 H, 0.7 M)
canvas = clip(U / 0.55) × [1 - 0.45 × clip((U - 0.65) / 0.35)]
B = mean over 80/160/240 km of max(L_sunward, 0.6 M_sunward)
score = (18 + 82 canvas)
        × (1 - 0.9 L)^1.3
        × (1 - 0.85 B)^1.2
        × [0.75 + 0.25 clip(V / 16000)]
```

The coefficients are **CH Weather design choices**, not coefficients fitted to
observed sunset ratings or prescribed by NOAA. The 18-point clear-sky baseline
allows some horizon color without a cloud canvas. Intermediate upper-cloud
amounts are favored over a completely filled cloud layer. Low clouds and sunward
low/mid cloud reduce the score. Visibility supplies a small attenuation penalty;
it is **not** a measurement or model of aerosol color enhancement.

Smooth once with a 0.65-native-cell Gaussian kernel, clip 0–100, and render filled
contours in five descriptive bands: 0–20 Limited, 20–40 Fair, 40–60 Good,
60–80 Very good, 80–100 Excellent. These categories describe the index, not a
probability, verified skill, hazard level, or promise of visible color.

### Three national highlights

Greedily select the highest land-grid score, suppress all grid points within
**600 km great-circle distance**, and repeat twice. The picks are relative to
that day's conditions, even on poor days. The metadata gives actual grid
coordinates, score, approximate sunset UTC, nearest reference city, and distance
to that city. Reference cities are a curated list in `sunset/cities.json`, not an
exhaustive geocoding database. A labeled city may be some distance from the peak.

### Limits and a validation path

Sunset color depends on cloud optical depth, phase/height, three-dimensional
illumination, aerosol size/composition, humidity, and the viewing horizon. HRRR
layer fractions and surface visibility do not fully describe those. This version
does not use satellite observations, aerosol/smoke forecasts, terrain, or an
ensemble. Tiny cloud-placement errors can reverse the outcome. The smoothing
and contour rendering do not add forecast skill.

Before describing this as a skillful forecast model, collect sunset photographs
with location/time and a consistent rating protocol, retain daily forecast grids,
compare scores against outcomes and a climatological/cloud-only baseline, and
evaluate a withheld period across regions and seasons. Then calibrate weights
and thresholds. Current tests check numerical and operational correctness,
**not meteorological predictive skill**.

## Reliability, storage, and website behavior

The first HRRR run used six hourly GRIB subsets (about 3.5 MB each) and completed locally in about 15 seconds including download, calculation and rendering. Each subset is bounded to 20 MB, with 15-second connect/90-second read timeouts and at most two retries. At most three cycles, each with 13 hourly subsets, can be attempted. NOAA requests are sequential with a one-second pause after each download. Natural Earth geography is retained in the Actions cache; raw GRIBs are not persisted between hosted jobs. No credentials or desktop session are required.

The PNG, binary lookup, lookup metadata and manifest are staged and validated before replacement. The JSON is written
last and carries the PNG's SHA-256. On download, calculation, or render failure,
the command returns nonzero and does not substitute synthetic weather. A process
crash between the final local renames could leave a mixed pair; normal hosted
publication avoids that window by deploying only after a successful complete
job. A failed deployment leaves the previous successful Pages site intact.

The homepage and `/sunset/` show the valid date, run, generation UTC and three
picks from JSON. The page explicitly labels a date that is not today's Eastern
date, and keeps old dates visible. If metadata cannot load, it tells the visitor
to check the printed date instead of calling the image current. Use an HTTP
server for JSON loading: `python -m http.server 8000`, then open
`http://localhost:8000/sunset/`. Direct `file://` opening can block `fetch`.

The static export allowlists website assets and all generated sunset files. It excludes
source code, caches, virtual environments, tests, and personal source documents.

```bash
python scripts/package_site.py --output-dir _site
python scripts/package_site.py --zip output/ch-weather-website.zip
```

The directory export must be a fresh path to avoid accidentally publishing stale
or unrelated files. The ZIP export can overwrite the existing site ZIP.

## Primary sources researched

- [NOAA JetStream: The Color of Clouds](https://www.noaa.gov/jetstream/clouds/color-of-clouds)
  explains why clouds can reflect red/orange illumination near sunrise/sunset.
- [NOAA: Clouds Outside](https://www.noaa.gov/sites/default/files/2023-03/CloudsOutMyWindow.pdf)
  describes mid/high clouds reflecting sunrise/sunset colors.
- [NOAA GML solar equations](https://gml.noaa.gov/grad/solcalc/solareqns.PDF)
  supplies the approximate solar timing/azimuth calculation.
- [NCEP HRRR products and extended cycles](https://www.nco.ncep.noaa.gov/pmb/products/hrrr/).
- [HRRR surface-file inventory](https://www.nco.ncep.noaa.gov/pmb/products/hrrr/hrrr.t00z.wrfsfcf02.grib2.shtml) identifies instantaneous layer cloud cover and surface visibility.
- [NOMADS HRRR filter](https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl) supplies the actual subsets.
- [Natural Earth](https://www.naturalearthdata.com/) supplies geographic boundaries.
- [GitHub schedule syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule)
  documents timezone-aware schedules; [schedule limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
  explains scheduling delays and inactive-repository behavior.
