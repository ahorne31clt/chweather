# Local National Weather Service forecasts

The `/outlooks/` page now includes a branded, interactive NWS point-forecast
section at `#local-forecast`. Charlotte, NC loads as the explicitly identified
default. Visitors can choose another US city/ZIP, enter coordinates, or request
browser location access. No location permission is requested automatically.

## Display

- The selected forecast period has a large forecast temperature, day/night
  styling, a code-drawn weather symbol, the original NWS short/detailed forecast,
  precipitation probability, wind, and exact local valid times.
- Up to 14 day/night periods appear in a horizontal, keyboard-accessible strip.
  These are the API's original periods, not manufactured daily highs/lows.
- The next 12 available hourly forecasts have temperatures and precipitation
  probabilities, with a simple relative-temperature visual.
- The issuing office, NWS update time, retrieval time, source link, manual
  refresh, and location-specific sunset link are included.

A forecast high/low is explicitly labeled as a **forecast**, not a current
observation. Null values remain “Not provided” or a dash; a real 0% probability
is displayed as 0%. Expired forecast periods are filtered, including on cache
hits. Data older than 24 hours carry a notice even if future periods remain.
No live warnings or current observations are inferred from forecast text.
The official forecast link also provides the visitor a route to current alerts.

## Sources and update behavior

1. Open-Meteo geocoding (GeoNames) resolves explicit city/ZIP searches. Coordinate
   input and browser location access skip geocoding.
2. `https://api.weather.gov/points/{latitude},{longitude}` supplies the current
   office/grid mapping, time zone, and official endpoint URLs.
3. Those NWS `forecast` and `forecastHourly` URLs are requested with `units=us`.
   The browser sends its normal User-Agent, Origin/Referer information and an
   `Accept: application/geo+json` header. No forbidden custom User-Agent is set.

Requests are made on page load for the default Charlotte forecast and on visitor
selection/refresh, **independent of the daily GitHub Actions graphics schedule**.
The component uses a small 10-minute in-memory cache, bounds request times,
retries transient NWS errors once, aborts superseded searches, and prevents a
slower old request from overwriting a newer location. Cached values are still
labeled with their actual update/retrieval times. Nothing is saved between
visits, and no API keys or extra environment variables are required.

The hourly endpoint can fail while the period forecast still displays. Failure
to get a usable period forecast shows an unavailable state with an official
source link; it does not display old values beneath a new city name or generate
replacement forecasts. Denied geolocation, unknown places, out-of-service-area
points, and missing values have explicit messages. NWS marine-only points may
not offer the standard land forecast used here.

The selected coordinates are sent to the NWS to retrieve the forecast. Typed
place searches are sent to the geocoder only on submission. No autocomplete
requests fire while typing. Open-Meteo's public geocoder is configured for the
site's non-commercial usage; review its terms if the service becomes commercial.

Primary documentation:

- https://www.weather.gov/documentation/services-web-api
- https://open-meteo.com/en/docs/geocoding-api

## Publish

Upload the updated GitHub-ready package, replacing matching paths while keeping
the existing `CNAME`. The existing workflow already triggers on `assets/**` and
`outlooks/**`; no new workflow or scheduled job is needed. After deployment,
the local forecast loads directly in the visitor's browser. Existing scheduled
map generation continues as before.

Rebuild packages with:

```bash
python scripts/package_site.py --zip output/ch-weather-website.zip
python -m scripts.package_github
```
