# CH Weather radar

Open `/radar/` through a web server (HTTPS or localhost). Radar loads directly from public NOAA data each time it is viewed. No credentials, API keys, environment variables, manual sign-in, or additional GitHub Actions job are required. Auto refresh checks every two minutes while the page is visible and playback is paused. The existing Pages workflow publishes the viewer and its local dependencies.

## Individual radar sites: genuine Level II

159 WSR-88D sites from https://api.weather.gov/radar/stations. Complete archive volumes come from https://unidata-nexrad-level2.s3.amazonaws.com . Select a site, product, and elevation sweep. Available sweeps differ by product; split-cut reflectivity and velocity sweeps are kept separate.

Products: reflectivity (dBZ), raw radial velocity (knots), correlation coefficient (ratio), differential reflectivity (dB), differential phase (degrees), and spectrum width (knots). Negative radial velocity is toward the radar; positive is away. Velocity is not dealiased or storm-relative. Range-folded and below-threshold gates remain missing. These moments are documented by NOAA ROC: https://www.roc.noaa.gov/level-two-data-types.php .

The original native gates are decoded in a Web Worker using the pinned MIT `nexrad-level-2-data` parser and bzip2 WebAssembly. Rendering projects gate ranges onto a geographic map using a 4/3-earth beam model. Archive times identify the start of a volume; later sweeps occur later. A 1600-pixel raster is generated for the selected range. Cursor values sample the rendered field on a four-pixel lattice, not a new observation at the cursor. Beam height, terrain blockage, clutter, and range limitations still apply. Do not interpret a missing gate as zero precipitation.

## MRMS

Source: https://noaa-mrms-pds.s3.amazonaws.com under `CONUS/`. Products: QC composite reflectivity, precipitation rate, and rolling 1-, 3-, 6-, and 24-hour radar-only precipitation accumulation. Accumulation ends at the displayed grid time and is an estimate in inches, not a gauge reading or forecast. Level II volumes do not directly contain accumulated precipitation: selecting accumulation switches to MRMS.

The browser decodes the actual 1 km GRIB2 product (template 5.41, 16-bit PNG packing), including its reference value and binary/decimal scaling. Zooming resamples the retained native grid for the visible map. Unsupported formats fail explicitly. Source files remain available through the Source file link. The viewer does not replace official warning services.

The timeline contains up to six completed files. Playback downloads/decodes scans on demand and caches up to eight rendered frames, so initial speed depends on the connection and device. Individual Level II files are limited to 30 MB and MRMS gzip files to 12 MB. Only one decoded native volume/grid is retained at a time. Auto refresh pauses in background tabs and during playback. Volume/grid times older than 20 minutes are marked stale, except the hourly 3/6/24-hour MRMS products, which use 100 minutes. Download errors clear the unavailable image and display the failure.

## Local build and export

The compiled worker, WASM, Leaflet, and licenses are already included in `assets/vendor/`; publishing requires no npm step. To rebuild the worker after source changes, use Node.js 22 or newer:

```
cd radar
npm ci --no-audit --no-fund
npm run build
npm test
```

Keep `assets/vendor/radar-worker.js` beside its generated `.wasm` file. Keep all Leaflet images and CSS. Serve WASM with `application/wasm` (GitHub Pages does). Main viewer source: `assets/radar.js`; worker and color scales: `radar/worker.mjs` and `radar/palettes.mjs`. Node dependencies are excluded from exports. Basemap attribution: OpenStreetMap contributors. Boundaries: Natural Earth public-domain geography. Bundled library licenses: `assets/vendor/RADAR-LICENSES.md`.

## Files added or changed

Added: `radar/index.html`, `radar/package.json`, `radar/package-lock.json`, `radar/build.mjs`, `radar/worker.mjs`, `radar/palettes.mjs`, `radar/zlib.mjs`, `radar/test.mjs`, `radar/BZIP2-LICENSE.txt`; `assets/radar.js`, `assets/radar.css`, `assets/radar-palettes.js`, `assets/radar-sites.json`, `assets/radar-boundaries.geojson`; `assets/vendor/leaflet.js`, `assets/vendor/leaflet.css`, `assets/vendor/images/*`, `assets/vendor/radar-worker.js`, `assets/vendor/radar-module-4PB7SZD3.wasm`, `assets/vendor/RADAR-LICENSES.md`; `docs/RADAR.md`.

Updated: `index.html`, `models/index.html`, `.gitignore`, `.github/workflows/sunset.yml`, `scripts/package_site.py`, `scripts/package_github.py`, `README.md`, `docs/REFRESHES.md`. Rebuilt export ZIPs under `output/` and the local `_site/` preview. Files inside `.cache/` and `radar/node_modules/` are local test/build artifacts and should not be uploaded.
