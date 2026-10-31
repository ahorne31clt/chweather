# WPC and CPC outlooks

The `/outlooks/centers.html` viewer contains 17 official graphics:

- WPC Excessive Rainfall Outlook Days 1, 2 and 3.
- WPC liquid-equivalent precipitation totals for Day 1 and cumulative Days 1–3, 1–5 and 1–7.
- CPC temperature and precipitation outlooks for Days 6–10, Days 8–14, Weeks 3–4, monthly and seasonal (the leading three-month calendar period printed on the map).

Maps and legends are preserved visually, including NOAA source/issuance/validity labels. No local forecast areas, percentages or current weather values are invented. Original GIF/JPEG images are decoded and saved as lossless PNG snapshots; map colors and pixels are not restyled. CPC and WPC have different products and category definitions; do not treat all shaded probabilities as chances of rain. Interpretation notes are provided for each selected graphic.

## Run and refresh

Use the existing pinned `requirements-sunset.txt` and Ubuntu setup in `docs/SUNSET.md`, then run:

```bash
python -m centers
```

No required environment variables, credentials, extra dependencies, desktop windows or manual login. The command downloads only 17 small official images (8 MB maximum per image, 15-second connect/45-second read timeouts), validates format, dimensions and static-frame count, converts to PNG, and stages all outputs before publishing `generated/centers/latest.json` last. Download, image decoding or output errors return nonzero and retain the previous publication. As with the other generators, a process crash during final local renames can interrupt a local publication; Actions deploys only a completed build.

Output: `generated/centers/latest.json` and 17 named PNGs. The manifest includes source URLs, official discussion-page URLs, dimensions, image hashes and exact retrieval UTC. HTTP Last-Modified, when present, is labeled source-file modification time. **Neither retrieval nor file modification is represented as forecast issuance or validity.** The exact issuance and valid interval are printed on every source graphic. The interface tells users to read those dates. A snapshot older than 30 hours receives a stale notice; validity cannot be inferred from the download time.

The existing daily 8 a.m. America/New_York GitHub Actions workflow now runs `python -m centers` before the models/export/deploy steps. Artifacts include the small center graphics. A successful all-product refresh is required; the source ZIP includes this package and the matching workflow. It intentionally excludes generated graphics; Actions creates them before export. Local website ZIP includes the snapshots.

Default view is the dated published snapshot. “Latest official graphic” requests the selected original directly from WPC/CPC and rechecks every five minutes while visible. Direct CPC images worked in browser testing; WPC blocked browser embedding in this environment. A failed direct load automatically returns to the dated snapshot with an explicit notice. Never claim a successful image download proves a newer forecast. The official-source/discussion link remains available. If the stored image also fails, hide the graphic and show a source-link fallback. Snapshot mode refreshes the manifest when Refresh is pressed; newer snapshots require a successful scheduled deployment.

CPC 6–10 and 8–14 day products are ordinarily updated in the afternoon Eastern time; the website's 8 a.m. snapshot may therefore retain the preceding afternoon's issuance. Monthly/seasonal products follow their own schedules. Always use the exact period printed on the map.

## Sources

- [WPC Excessive Rainfall Outlook](https://www.wpc.ncep.noaa.gov/qpf/excess_rain.shtml): `94ewbg.gif`, `98ewbg.gif`, `99ewbg.gif`.
- [WPC precipitation forecasts](https://www.wpc.ncep.noaa.gov/qpf/day1-7.shtml): `fill_94qwbg.gif`, `d13_fill.gif`, `p120i.gif`, `p168i.gif`.
- [CPC 6–10 day](https://www.cpc.ncep.noaa.gov/products/predictions/610day/), [8–14 day](https://www.cpc.ncep.noaa.gov/products/predictions/814day/), [Weeks 3–4](https://www.cpc.ncep.noaa.gov/products/predictions/WK34/), [monthly](https://www.cpc.ncep.noaa.gov/products/predictions/30day/), [leading seasonal outlook](https://www.cpc.ncep.noaa.gov/products/predictions/long_range/seasonal.php?lead=1). The seasonal images use `long_range/lead01/off01_temp.gif` and `off01_prcp.gif`, not a multi-season overview mosaic.

## Exact files added or replaced

Added: `centers/__init__.py`, `centers/__main__.py`, `outlooks/centers.html`, `assets/centers.js`, `assets/centers.css`, `tests/test_centers.py`, `docs/CENTERS.md`, and generated `generated/centers/latest.json` plus 17 `wpc-*.png`/`cpc-*.png` graphics enumerated in that manifest.

Replaced: `index.html` (homepage directory link), `outlooks/index.html` (WPC/CPC links), `.github/workflows/sunset.yml` (new refresh step, push path and artifact), `scripts/package_site.py`, `scripts/package_github.py` (export/source packaging), `README.md`, `docs/REFRESHES.md`, `output/ch-weather-github-ready.zip`, `output/ch-weather-website.zip`. Matching `_site/` preview copies are refreshed. Existing Python model and sunset calculations are unchanged.

Upload the extracted source ZIP contents with folders preserved, replacing files including the workflow and `centers/` package; keep the existing CNAME. Run the updated Actions workflow once after uploading. No new secret is required.

## Verification

All 17 snapshots were fetched from their real official sources and opened in the browser. Checked period/field selection, paired CPC temperature/precipitation periods, mobile layout, CPC direct-source mode and WPC snapshot fallback. Automated tests verify the 17-product catalog, leading seasonal source selection, unchanged image pixels, file-time/issuance separation, rejection of HTML in place of images, and preservation of the last publication when a download fails. The complete suite passed 44 tests.
