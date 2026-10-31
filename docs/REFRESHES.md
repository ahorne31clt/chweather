# What refreshes automatically

The replacement workflow is `.github/workflows/sunset.yml`, named **Daily weather and sunset outlooks**. It starts at 8 a.m. America/New_York and additionally at 05:30, 11:30, 17:30, and 23:30 UTC for six-hour refreshes. Daylight saving time is handled for the 8 a.m. start. It also supports **Run workflow** and relevant pushes to `main`. Upload the matching workflow along with the source; the older sunset-only workflow cannot generate all the files now required by the site. See [repair instructions](FIX-AUTOMATIC-UPDATES.md).

| Step | Command | Outputs refreshed |
| --- | --- | --- |
| Sunset | `python -m sunset` | Sunset graphic, metadata, and location lookup |
| Weather/outlooks | `python -m weather` | SPC Days 1–3, national/NC weather, precipitation chances, dated foliage estimate |
| Tropical | `python -m tropical` | Atlantic/Eastern/Central Pacific 2-day/7-day official graphics and bulletins |
| WPC/CPC | `python -m centers` | Official rainfall and climate outlook graphics |
| ENSO | `python -m enso` | Official status, indices, and forecast graphic |
| RTMA | `python -m analysis` | Surface analyses and METAR plots |
| Ensembles | `python -m ensembles` | REFS and GEFS probabilities |
| Models | `python -m models` | GFS, HRRR, NAM parameters, numeric probes, smoothing layers, and GFS/HRRR airport meteograms |
| Publication | `python scripts/package_site.py --output-dir _site` | One Pages deployment containing the site and matching generated data |

Generation runs in eight parallel jobs (maximum four at once), each validating its output before artifact transfer. Generation is not instantaneous: model downloads and rendering finish after the scheduled start. A failed required step prevents a new deployment. The website keeps the last successful publication and its original issue/valid/generation times. No weather values are synthesized to cover a failed source. Forecast assets are not committed by the job; they are assembled into the Pages artifact. An open model viewer checks the published manifest every five minutes and when its tab becomes visible, adopts new publications, preserves the nearest valid time, and invalidates airport-data caches. It pauses updates while a guide or airport dialog is open.

The local NWS point forecast makes fresh browser requests when viewed/refreshed. The tropical page also offers direct official image loading when the browser/source permits it. The radar viewer fetches public Level II volumes and MRMS grids directly in the browser, with a two-minute auto-refresh while visible. These requests are independent of the scheduled publication. See `docs/RADAR.md`.

## GitHub update needed

When the repository was checked on October 30, 2026, GitHub still had the older **Daily sunset outlook** workflow, which runs only `python -m sunset`. Its successful manual run does not mean the later model/weather/tropical generators are installed.

1. Extract `output/ch-weather-github-ready.zip`.
2. Upload its contents at the repository root with folders intact, replacing matching files. Keep the existing CNAME.
3. Replace `.github/workflows/sunset.yml` with the included version. If browser upload hides `.github`, edit that existing file directly on GitHub and paste the complete local replacement.
4. Keep Settings → Pages → Source set to **GitHub Actions**.
5. Open Actions → **Daily weather and sunset outlooks** → **Run workflow** on `main` and wait for the final Pages deployment to succeed.

Upload the updated Python packages, assets, tests, and requirements along with the workflow; replacing only the workflow while the scripts are absent will fail. The source ZIP deliberately omits generated forecasts, making browser upload smaller. The workflow regenerates them. `output/ch-weather-website.zip` is the separate complete static-hosting export containing forecast assets.

All required environment variables: **none for the weather/model/tropical generators**. GitHub supplies its own deployment token and Pages environment through Actions permissions; no weather API secrets are required.

## WPC and CPC

The updated daily workflow also runs `python -m centers` to publish 17 official WPC/CPC graphic snapshots before export. Upload its matching `centers/` source package and workflow. Products and exact validity/retrieval distinctions are documented in `docs/CENTERS.md`. No extra credentials.

## RTMA / METAR

The daily workflow now includes `python -m analysis`. It creates a dated analysis and station snapshot, not a continuously live stream. Station times and RTMA valid time remain separate. See `docs/ANALYSIS.md`; upload the matching analysis package and workflow.

## MOS bulletin viewer

The MOS page fetches the latest available original bulletin directly from IEM when requested or refreshed. It does not depend on the 8 a.m. generation job. No additional scheduled command or credentials. See `docs/MOS.md`.

## Ensemble probabilities

The daily workflow now runs `python -m ensembles` with the matching `ensembles/` source package. It publishes real REFS probabilities and GEFS probabilities computed from all 31 members, with explicit per-product valid intervals. No credentials. See `docs/ENSEMBLES.md`.

## ENSO tracker

The daily workflow runs `python -m enso` to refresh official CPC status, observed RONI/ONI and weekly Niño 3.4 indices, and the official forecast graphic. Source components have different update schedules; the tracker labels their actual dates. See `docs/ENSO.md`.
