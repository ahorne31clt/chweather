# MOS bulletin lookup

Open `/mos/`. This plain HTML/CSS/JavaScript page requests the latest available original NWS text bulletin from the Iowa Environmental Mesonet's documented ASCII service. No API key, environment variables, backend, additional dependencies, or new scheduled generation step is needed. The existing site deployment exports this page; `mos/**` is included in workflow push paths.

Products: GFS short-range MAV, NAM MET, extended GFS MEX, and GFS LAMP LAV. The viewer currently supports CONUS K-prefixed ICAO stations and three-character FAA identifiers, with optional airport-name/city/IATA lookup using the existing OurAirports catalog under `generated/models/airports/catalog.json`. The catalog is a station-location aid, not a guarantee of MOS availability. Direct ICAO/FAA lookup still works if the catalog is unavailable. Alaska/Hawaii/territory and other non-K station naming is intentionally not guessed; use the IEM source tools for those stations.

## Data and validation

IEM's documented identifier convention is product plus the three-character station suffix, e.g. `MAVCLT`. Request `https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?pil=MAVCLT&limit=1`, similarly METCLT/MEXCLT/LAVCLT. The service has browser CORS support. Every request has a 20-second timeout; a new selection aborts the old request and hides the old bulletin. Only the latest response can update the page. The bulletin must have exactly one recognized station/product header matching the requested selection, a valid initialization date, a forecast time row (HR/UTC/FHR), and a temperature row. Future initialization more than ten minutes ahead, HTML error pages, missing rows and oversized text are rejected. Missing/unavailable guidance never triggers a different station or model substitution.

Display strips transport control characters and normalizes line endings while retaining coded weather rows, spacing, dates and source/WMO header. Text is inserted with `textContent`, never HTML. TXT download retains the original provider response including transport control characters; Copy uses the clean displayed text. Bulletins are not synthesized from JSON or reformatted into potentially misleading decoded data. This avoids treating categorical QPF, missing codes, conditional probabilities or special wind codes as ordinary numeric measurements.

The exact bulletin initialization and browser retrieval time are shown separately in UTC. HR and UTC refer to forecast-valid clock hours and must be read with the bulletin's calendar dates; FHR refers to hours after initialization. MEX, MAV, MET and LAV may have different latest cycles and valid periods. Mark guidance older than 18 hours for MAV/MET, 30 hours for MEX, or 3 hours for LAV as older guidance, without falsely claiming it is expired. No automatic polling; Refresh asks for the provider's latest available bulletin. Copy-link preserves station and product, not a historical cycle, so a later visitor may see a newer bulletin.

MOS is statistical model guidance, not a forecaster-issued NWS point forecast, current observations or a TAF. The guide identifies common row units and refers coded categories and product-specific interval definitions to the official references. Blank/missing values stay blank/missing. No forecast confidence or skill claims are added.

## Sources

- [IEM MOS service and synthetic station identifiers](https://mesonet.agron.iastate.edu/mos/).
- [NWS MAV card](https://vlab.noaa.gov/web/mdl/mav-card).
- [NWS MEX card](https://vlab.noaa.gov/web/mdl/mex-card).
- [NWS MOS product cards, including MET](https://vlab.noaa.gov/web/mdl/mos-product-cards).
- [NWS LAMP](https://vlab.noaa.gov/web/mdl/lamp).

## Exact files added or replaced

Added: `mos/index.html`, `assets/mos.js`, `assets/mos.css`, `docs/MOS.md`.

Replaced: `index.html`, `outlooks/index.html`, `models/index.html`, `analysis/index.html` (navigation links); `scripts/package_site.py` (export allowlist); `.github/workflows/sunset.yml` (push path); `README.md` and `docs/REFRESHES.md` (documentation); `output/ch-weather-github-ready.zip`, `output/ch-weather-website.zip` (packages). Matching `_site/` preview files are refreshed. No Python forecast/analysis generator or dependency file changed.

Upload extracted source ZIP contents with folders preserved, replacing existing files. Keep the existing CNAME. No new secret or Actions data-refresh command is required. The source ZIP has more than 100 files, so GitHub browser uploads may need two folder-preserving batches. Edit the existing `.github/workflows/sunset.yml` through GitHub's file editor if the upload picker hides it.

## Verification

Verified live KCLT bulletins for MAV, MET, MEX and LAV, including the MEX FHR row and LAV half-hour initialization. Checked city search ranking (Raleigh → KRDU), ICAO lookup, raw TXT download, shareable station/product URLs, unavailable-product and network-error responses that hide the previous bulletin, older-guidance notices, and mobile horizontal bulletin scrolling without page overflow. Action feedback is separate so copying does not remove an older-guidance warning. No synthetic weather is shipped as a fallback.
