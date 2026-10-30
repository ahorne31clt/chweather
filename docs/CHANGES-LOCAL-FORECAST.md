# Exact changes: local NWS forecast component

Paths are relative to the CHWeather Site repository root.

## Added

- `assets/local-forecast.html`: editable component template and attribution.
- `assets/local-forecast.js`: NWS requests, city/ZIP search, browser location,
  cache/race/error handling, period selection, symbols, hourly strip and sunset link.
- `assets/local-forecast.css`: responsive component styling in the existing palette.
- `docs/LOCAL-FORECAST.md`: sources, behavior, privacy and publishing instructions.
- `docs/CHANGES-LOCAL-FORECAST.md`: this list.

## Modified

- `outlooks/index.html`: include the new local forecast and its CSS/JavaScript.
- `assets/outlooks.js`: preserve the `#local-forecast` anchor on initial load.
- `assets/sunset-search.js`: accept explicit location links from the local forecast.
- `scripts/package_site.py`: include the new documentation in the export.
- `README.md`: describe the new component.
- `output/ch-weather-website.zip`: updated static export.
- `output/ch-weather-github-ready.zip`: updated source/website package.

No forecast generator, dependency file, scheduled workflow, original logo,
headshot, or existing forecast graphic changed. Local preview copies are ignored
verification artifacts. Nothing was uploaded or deployed to GitHub by this chat.
