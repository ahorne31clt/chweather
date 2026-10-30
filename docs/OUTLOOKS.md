# Weather outlooks and sunset location search

## What is included

- `/outlooks/`: four product groups and national/North Carolina region controls.
- Official **SPC Day 1, Day 2, and Day 3 categorical outlooks**, redrawn in CH Weather style.
- **National and North Carolina weather-overview maps:** NWS daytime highs with
  precipitation probabilities at selected cities for the same 12-hour interval.
- **National and North Carolina precipitation maps:** official NDFD 12-hour PoP.
- **National and North Carolina fall color maps:** Explore Fall's published dated
  categorical raster, preserving the source colors and Web Mercator bounds.
- `/sunset/`: city/state, ZIP code, coordinate, and optional browser-location lookup
  against the actual published sunset score grid.

These are real-data presentations. The weather-overview maps are not separately
hand-analyzed CH Weather forecasts, SPC categories are not modified, and foliage
color stage is not inferred from a generic weather or calendar formula.

## Commands and dependencies

The existing Ubuntu dependencies in `requirements-sunset.txt` are sufficient:

```bash
sudo apt-get update
sudo apt-get install -y python3-venv libeccodes0
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-sunset-dev.txt
python -m pytest -q tests
python -m sunset
python -m weather
python scripts/package_site.py --output-dir _site
```

Use a fresh `_site` destination. `python -m sunset` now additionally creates
`generated/sunset/lookup.json`; `latest.json` identifies and fingerprints that
grid. `python -m weather` creates `generated/weather/latest.json` and nine PNGs
in the same folder during foliage season. The weather manifest lists the
available images, sources, issuances, and valid periods. Images are 2400 × 1500.

Create an updated repository upload ZIP with:

```bash
python -m scripts.package_github
```

The workflow file is still **`.github/workflows/sunset.yml`**. Replace the existing
file at that exact path; do not add another competing publishing workflow. Its
name in Actions is now **Daily weather and sunset outlooks**. Run it manually
from the Actions tab or let its existing 08:00 America/New_York schedule run.
Relevant source/website pushes to `main` also trigger it. Change that branch name
if your repository's default branch differs. Pages must use GitHub Actions as
its source. Keep your existing `CNAME` and domain settings.

This does not remotely update GitHub by itself: upload the changed source files
or the extracted GitHub-ready ZIP, preserving folder structure. Your local
`.venv`, caches, and `_site` export do not belong in the repository. GitHub jobs
install dependencies automatically; your own computer need not stay running.

## Source and interpretation details

### SPC

Data: `https://www.spc.noaa.gov/products/outlook/day{1,2,3}otlk_cat.nolyr.geojson`.
The matching `day{n}otlk.txt` supplies the official discussion and timestamps,
including when a GeoJSON contains no risk polygons. The pipeline verifies that
the text and polygons share an issuance, retries the pair once during an update,
rejects unknown categories rather than guessing their meaning, and preserves
the original category ordering. Empty polygons mean no outlined categories;
they do not imply an error or fabricate a thunderstorm area.

Source page: https://www.spc.noaa.gov/products/outlook/

### NWS weather overview and precipitation

Source: NDFD CONUS days 1–3 files `ds.maxt.bin` and `ds.pop12.bin` from:

`https://tgftp.nws.noaa.gov/SL.us008001/ST.opnl/DF.gr2/DC.ndfd/AR.conus/VP.001-003/`

The generator selects the first unexpired daytime interval ending at 00 UTC and
requires the high-temperature and PoP periods to match. It decodes the actual
GRIB period duration and verifies a 12-hour interval. A PoP map is the chance of
more than 0.01 inch / 0.254 mm of liquid-equivalent precipitation at a point in
that interval, including frozen precipitation. **It is not a daily/24-hour
probability.** No two PoPs are added, averaged, or maximized to invent one.

The native grids are about 2.5 km. Every second grid point is retained for modest
runner memory/time; maps sample nearest available data onto a 0.25° national or
0.05° NC display grid. No weather information is extrapolated across large
missing-data gaps. Exact state/national boundaries clip the contours. Graphic
resolution does not imply additional meteorological resolution. City tables
provide readable source values on mobile.

NWS background: https://vlab.noaa.gov/web/mdl/ndfd

### Explore Fall

This is the provider found in the earlier Remotion project. Its public map script
identifies dated rasters at:

`https://www.explorefall.com/maps/YYYY-highres/YYYYMMDD.png`

and Web Mercator image corners `[-126,52],[-65,52],[-65,23],[-126,23]`. The generator
uses the current Eastern date, with at most two prior dates as a clearly dated
fallback. Source pixels, categories, and colors are preserved. It does not
present fallback data as today's estimate. These products run September–December;
outside those months the manifest records `out_of_season` and the page links to
the provider. A failed in-season source download is not replaced by a synthetic
foliage map.

The provider's `https://api.explorefall.com/v1/location-forecast` endpoint returned
**HTTP 403** during verification, just as it did in the earlier project. No access
control is bypassed, and no peak dates are claimed from that API. The displayed
maps come from the publicly published raster, not an authenticated API response.
For interactive reports, location forecasts, and future dates, use the provider:

- https://www.explorefall.com/fall-foliage-map
- https://www.explorefall.com/blog/2026/mastering-the-map

The source's model estimate can differ from individual species, slopes, streets,
and direct observations. Attribution remains on the images and webpage.

## Sunset lookup

`lookup.json` contains the existing 0.25° forecast grid, scores, approximate
sunset UTC minutes (which may exceed 1440), a simplified contiguous-US land
boundary, valid date, run, generation time, and matching image fingerprint.
Offshore/out-of-domain cells are null. The lookup uses the closest valid cell
within 35 km, never one of the three national picks. Outside-CONUS searches are
rejected; the distance and actual grid coordinates are disclosed. A date that
is not today's local date is labeled accordingly. No score is called a percent.

City/ZIP searches use Open-Meteo's geocoding service (GeoNames data) on explicit
form submission, with results limited to the US and ambiguous matches offered
as choices. No autocomplete request fires on every keystroke. Coordinate input
and optional browser geolocation require no geocoding call. Geolocation requires
the visitor's permission and HTTPS (localhost is also allowed). Those coordinates
stay in the browser. Denied permission and out-of-area results have usable
fallbacks rather than invented forecasts.

Geocoder documentation: https://open-meteo.com/en/docs/geocoding-api
The configured public geocoder is for non-commercial use; review the provider's
terms or replace it with a suitable backend/provider if this becomes a commercial
service. Do not put paid API secrets in browser JavaScript. The geocoder is the
only external service contacted by the sunset search, only when submitted.

## Environment variables, reliability, and publication

**No new required environment variables or credentials.** Existing optional
Requests proxy/CA settings and Matplotlib cache settings still apply. There is
no Explore Fall API credential or undocumented bearer-token configuration in
this version. Never paste keys into the repository or frontend JavaScript.

NOAA, NDFD, and public foliage maps download only in Actions, not once per site
visitor. NDFD downloads are capped at 20 MB per file; SPC at 2 MB and its text at
1 MB; the foliage PNG at 8 MB. Typical measured source downloads are much smaller
(about 6 MB NDFD, less than 0.3 MB foliage, tiny SPC files). Geography is cached.
Rendering is headless and sequential. The workflow's 20-minute cap remains.

Both generators fail nonzero on required download/processing/render failures.
The new weather manifest is only replaced after the complete batch renders.
The complete static site deploys after all tests and generation steps succeed,
so an upstream failure leaves the previous deployed site in place. Product
expiry/date warnings are shown rather than suggesting old guidance is current.

These are scheduled snapshots. SPC guidance can change several times daily;
the morning run is not a continuously updating warning feed. Source links and
valid times remain prominent, including when a newer issuance exists at SPC.
The scheduled start is 8 a.m. Eastern; GitHub may delay the job and publication.
