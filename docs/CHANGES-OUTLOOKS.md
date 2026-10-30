# Exact changes: expanded outlooks and sunset location search

All paths are relative to the CHWeather Site repository root.

## Modified

- `.github/workflows/sunset.yml`: rename the Actions display name, test all tests,
  generate the new products, include lookup/data artifacts, trigger on the new
  source/page paths, and cache regional geography.
- `sunset/__main__.py`: export the actual location lookup grid and matching fingerprints.
- `scripts/package_site.py`: export the outlook page, documentation, lookup grid,
  and every graphic listed by the current weather manifest.
- `index.html`: add Weather Outlooks navigation and the product-directory section.
- `sunset/index.html`: add Weather Outlooks navigation and location search.
- `assets/styles.css`: responsive outlook controls, source tables, location forms/results.
- `build_site.py`: keep initial homepage generation consistent with the new directory/navigation.
- `README.md`: document the expanded products and commands.
- `output/ch-weather-website.zip`: refreshed static export.
- `output/ch-weather-github-ready.zip`: refreshed source/website upload package.
- `generated/sunset/latest.png`: regenerated from real GFS data.
- `generated/sunset/latest.json`: regenerated and identifies the location grid.

## Added

- `weather/__init__.py`
- `weather/__main__.py`
- `weather/sources.py`
- `weather/render.py`
- `outlooks/index.html`
- `assets/outlooks.js`
- `assets/outlook-directory.html`
- `assets/location-search.html`
- `assets/sunset-search.js`
- `scripts/package_github.py`
- `tests/test_weather.py`
- `docs/OUTLOOKS.md`
- `docs/CHANGES-OUTLOOKS.md`
- `generated/sunset/lookup.json`
- `generated/weather/latest.json`
- `generated/weather/spc-day1.png`
- `generated/weather/spc-day2.png`
- `generated/weather/spc-day3.png`
- `generated/weather/weather-national.png`
- `generated/weather/weather-nc.png`
- `generated/weather/rain-national.png`
- `generated/weather/rain-nc.png`
- `generated/weather/foliage-national.png`
- `generated/weather/foliage-nc.png`

Local download caches, test caches, and QA images are ignored verification files.
Dependencies are unchanged. The original logo, headshot, portfolio pages, social
embeds, and résumé PDF are unchanged by this update. No GitHub repository files
were remotely changed or deployed by this chat. Preserve the repository's existing
`CNAME` and custom-domain settings when uploading this update.
