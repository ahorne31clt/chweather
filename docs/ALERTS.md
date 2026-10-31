# Current warnings and alerts

`/alerts/` displays current National Weather Service warning/watch/advisory bulletins. The homepage has North Carolina, nationwide/marine, and tornado-warning counters linking to filtered views. No API key, environment variables, dependencies, backend, or extra Actions generation job is required. The browser requests `https://api.weather.gov/alerts/active` with GeoJSON Accept headers; normal browser identification is used (JavaScript cannot set User-Agent). Existing daily Pages deployment packages the page, and `alerts/**` is included in workflow push paths.

## Counts and current-data behavior

- Counters count distinct active NWS **bulletins**, not weather events, storms, counties or people. Tornado and severe-thunderstorm watches can appear as WFO-issued bulletins; these counts are not counts of unique SPC watch areas.
- Only Actual-status Alert/Update messages are displayed. Test, Exercise, Draft and Cancel messages are excluded. Actual Update/Cancel references remove replaced IDs; duplicate IDs use the latest sent time. Expired messages or hazards whose explicit ends time has passed are removed locally every 30 seconds.
- All warnings, tornado warnings, severe thunderstorm warnings, flash flood warnings and all watches are counted separately. Subset warnings are already included in all warnings, so do not sum the cards. Clicking a card filters the list.
- State filtering uses the state prefix of official UGC land-zone/county codes. Marine filtering uses official marine UGC prefixes (including coastal waters and Great Lakes) and marine-zone links. NWS also serves marine zones under `/zones/forecast/`, so URL path alone is insufficient. Nationwide includes NWS land and marine coverage, including Alaska, Hawaii and US territories. A multi-state bulletin is counted once nationally but can appear in each relevant state view.
- Counters follow the state/coverage selection. Type and text filters affect only the list. Search matches event, area description, headline or issuing office; it is not coordinate-level warning verification. Results are sorted by a documented presentation priority (tornado/tsunami, flash flood, severe thunderstorm, hurricane/storm surge, then other warnings/watches/advisories and severity), newest issued, or expiration. This ordering is not an NWS hazard ranking.
- Pagination is followed on the API's own HTTPS alerts host, at most eight pages and 5,000 bulletins. A partial/error response is rejected; counts are never taken from an incomplete list. Each request has a 20-second timeout. No scraping or manufactured weather values.
- Full alert page checks every minute while visible; homepage every two minutes. Returning to the tab triggers a check if more than one minute has elapsed. Each view labels last successful check and feed-updated time separately. NWS caching/processing may delay changes; this is not push notification delivery.
- A failed request changes counts to unavailable (—). Any remaining cached bulletins are visibly labeled last snapshot. A feed-updated timestamp more than 30 minutes old is marked delayed and counters suppressed; five minutes without a successful check is also stale. Valid zero is shown only after a successful, current feed response.
- Issued, expiration, onset and explicit hazard-end times remain distinct and use the browser's local time zone. Official description and protective instructions are rendered as plain text, never HTML. Alert source links use validated NWS URLs. Details remain available without invented summaries or hazard claims.

The page is not an emergency notification system. Use Wireless Emergency Alerts, NOAA Weather Radio and official local channels for time-sensitive information. NWS warning/watch/advisory terminology is explained alongside links to local forecasts, SPC and tropical outlooks.

Sources: [NWS API documentation](https://www.weather.gov/documentation/services-web-api), [NWS alert information](https://www.weather.gov/alerts), [active GeoJSON](https://api.weather.gov/alerts/active).

## Exact files added or replaced

Added: `alerts/index.html`, `assets/alerts.js`, `assets/alerts.css`, `docs/ALERTS.md`.

Replaced: `index.html` (homepage warning summary and navigation); `outlooks/index.html`, `sunset/index.html`, `tropical/index.html`, `satellite/index.html`, `models/index.html` (warning links); `scripts/package_site.py` (export allowlist); `.github/workflows/sunset.yml` (push path); `README.md` (feature documentation); `output/ch-weather-github-ready.zip`, `output/ch-weather-website.zip` (packages). Matching `_site/` preview copies are refreshed. Existing generated forecasts and Python meteorology code are unchanged.

Upload extracted GitHub-ready ZIP contents with folders preserved, replacing existing source files and keeping the current CNAME. No new secret or scheduled backend refresh is required for these browser-loaded alerts.

## Verification

Checked the real NWS feed on desktop and 390-pixel mobile, state and marine filters, type-counter links, expandable instructions and the homepage summary. Browser-isolated synthetic fixtures verified exact counts after duplicate IDs, update references, cancellations, expiry and test-message exclusion; marine forecast-zone codes; plain-text handling of HTML in alert descriptions; and unavailable counters after a failed refresh. Synthetic fixtures are not shipped or displayed as current weather.
