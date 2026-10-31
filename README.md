# CH Weather

Static HTML, CSS, and JavaScript. No build system, account, or paid service required.

**Automatic-update repair:** upload the matching `.github/workflows/sunset.yml` together with all source files. The old sunset-only workflow cannot build the current site. The replacement generates every product, including models and airport meteograms, at 8 a.m. Eastern and every six hours. Follow [the exact repair steps](docs/FIX-AUTOMATIC-UPDATES.md), including changing Pages source to GitHub Actions and starting a fresh workflow run.

## Weather outlooks and location search

The outlook page now also includes an interactive **local NWS forecast**: city/ZIP or coordinate search, optional browser location, day/night period selection, the next 12 hourly forecasts, original NWS narrative, precipitation chances, wind and update times. Charlotte loads as the labeled default. This data is retrieved on demand from the NWS, independently of the scheduled map graphics. See [component details](docs/LOCAL-FORECAST.md) and [exact changed files](docs/CHANGES-LOCAL-FORECAST.md).

The `/outlooks/` page now includes official SPC Days 1–3, national and North Carolina NWS weather graphics, 12-hour precipitation-chance maps, and attributed Explore Fall foliage-model maps. `/sunset/` supports city/ZIP, coordinates, and optional browser-location lookup using the actual published score grid. Run `python -m sunset` and `python -m weather`; the existing daily workflow now generates and publishes both. See [sources, commands, and interpretation](docs/OUTLOOKS.md) and [the exact file-change list](docs/CHANGES-OUTLOOKS.md). Create a complete GitHub-ready ZIP with `python -m scripts.package_github`.

## Daily sunset outlook

The experimental outlook uses real NOAA HRRR 3-km hourly cloud and visibility data from extended 48-hour cycles and renders a branded CONUS graphic with three highlights at least 600 km apart. After installing `requirements-sunset.txt`, run **`python -m sunset`**. Website-ready outputs are `generated/sunset/latest.png` and `generated/sunset/latest.json`. See [complete Ubuntu installation, GitHub Pages scheduling, methodology, environment variables, and limitations](docs/SUNSET.md). No weather API credentials or required environment variables are needed. Remote scheduling is not active until this repository is uploaded to GitHub and Pages is configured.

The website has a homepage outlook section and `/sunset/` page. The About page now uses Christopher's supplied headshot. For a safe static export, use `python scripts/package_site.py --zip output/ch-weather-website.zip`.

## Preview

Run `python -m http.server 8000` in this folder and visit http://localhost:8000. The portfolio begins at `/portfolio/` and the forecast at `/sunset/`. Opening `index.html` directly also shows the static content, but browsers can block forecast JSON loading over `file://`.

## Edit

- `index.html`: main CH Weather placeholder.
- `portfolio/index.html`: portfolio overview.
- Other `portfolio/*.html` files: individual portfolio pages. All page content is plain HTML.
- `assets/styles.css`: colors, typography, layout, responsive styling, and motion.
- `assets/site.js`: mobile navigation and coursework filters.
- `assets/ch-weather-logo.png`: original logo, copied without modification.
- `assets/contours.svg`: decorative contours, not weather observations or model data.
- `output/pdf/christopher-horne-resume-placeholder.pdf`: replace with the finished résumé and update the link/label in `portfolio/contact.html`.

Navigation and footer markup are present in each HTML file so pages work without JavaScript. Update each page when changing navigation. Optional Google Fonts load Barlow and Barlow Condensed; local system fonts work when offline.

`build_site.py` is the initial generation script and requires reportlab. It is not needed to edit, preview, or host this site. Avoid rerunning it after manual HTML edits; it rewrites the generated pages and placeholder PDF.

## Model room

`/models/` is the map-first GFS/HRRR viewer. Choose GFS, HRRR, or NAM 12 km. Parameters include precipitation type/pressure/thickness, 2 m temperature/dewpoint/humidity, 10 m wind, sea-level pressure, surface-based CAPE, 500 mb height/wind, and absolute vorticity from real NOAA data. NAM omits the unsupported instantaneous precip product and airport rate meteograms. Region presets, matching UTC valid times between models, loop bounds, forecast-hour jump, pinned legends, and shareable URLs improve navigation. Temperature/dewpoint maps include dense values and pointer/tap readouts that account for zoom and pan. State/country borders are dark for contrast, and 500 mb wind maps include barbs. The Meteogram button searches CONUS airports and charts model temperature, 10 m sustained wind, and instantaneous precipitation rate; PNG and CSV downloads are available. GFS covers the full 384-hour horizon every three hours; HRRR prefers 48-hour extended cycles and falls back to 18 hours when necessary. Generate with `python -m models`; the daily workflow runs this before publishing. See [model setup and science](docs/MODELS.md) and [exact changed files](docs/CHANGES-MODELS.md). The GitHub source ZIP excludes model images; Actions generates them. The static website ZIP includes the generated frames.

## Social embeds

Instagram @chweather, X @chornewx, and YouTube @chornewx appear on the dedicated `portfolio/social.html` page. Instagram uses its native profile embed, framed to display its post grid beneath a charcoal profile header without recoloring the media, X its official timeline widget, and YouTube the verified channel introduction video. The embeds depend on platform availability, public-account/embed settings, and the visitor's browser. Direct profile links remain available. No paid feed service or API keys are needed. YouTube video ID: `ytZDTcEJkys`; verified channel ID: `UCu67Ke4SnF9scSaNyT9anPQ`. Replace the player URL when you want to feature another video. `assets/social-section.html` is the generation template; the published HTML contains its markup directly.

## Adding projects

Replace the planned entries in `portfolio/projects.html` with real titles, dates, descriptions, and links. Put PDFs/slides in a new `assets/projects/` folder. Keep the Coming soon label until an actual artifact is available. Interactive projects can live in their own subfolders.

## Hosting later

Use `python scripts/package_site.py --output-dir _site` and upload that fresh export to any static host. It includes the homepage, assets, portfolio, sunset page, generated forecast, documentation, and placeholder résumé. No subdomain is required. `/portfolio/` and `/sunset/` are paths on the same domain. The sunset pipeline uses real HRRR forecast data; there is no live-conditions feed, analytics, form service, or stored credential. Daily GitHub Pages deployment setup is in `docs/SUNSET.md`.

The transcript is deliberately not included in the website files. Grades, GPA, birth date, and withdrawn/failed coursework are not published. Courses currently being repeated appear only in the current category. Spring 2027 courses are planned, not confirmed enrollment.

## Tropical outlooks and refresh setup

`/tropical/` shows official NHC/CPHC 2-day and 7-day outlooks for three basins, with dated bulletins and system snapshots. Generate with `python -m tropical`. All model parameters now have raw-value cursor/tap readouts; Native/Smooth changes only the color-field presentation, keeping annotations sharp. See `docs/TROPICAL.md`, `docs/MODELS.md`, and `docs/REFRESHES.md`. The replacement daily workflow includes all implemented generators. Upload its matching scripts as well as the workflow; the checked remote repository still had the older sunset-only version.

## Satellite viewer

`/satellite/` loads timestamped NOAA GOES-East/West imagery directly in the browser, with GeoColor, infrared, water vapor, regional/full-disk views, loops, zoom/pan and automatic refresh. No additional generation job or credentials. See [viewer details and exact changed files](docs/SATELLITE.md).

## Current warnings and alerts

`/alerts/` and the homepage show official NWS active warning bulletin counters, with state/type/search filters, full instructions, expiration times and clear stale/unavailable states. Data refreshes directly in the browser; no additional Actions generation step or credentials. See [alert behavior and exact changed files](docs/ALERTS.md).

## WPC and CPC outlooks

`/outlooks/centers.html` provides official excessive-rainfall, precipitation-total and temperature/precipitation outlooks through seasonal guidance. Generate 17 dated graphics with `python -m centers`; the daily workflow now includes this command. See [products, setup, interpretation and exact changed files](docs/CENTERS.md).

## RTMA and station plots

`/analysis/` shows native RTMA surface analyses and separately timestamped METAR station plots, with region/field/density controls, station lookup and PNG export. Generate with `python -m analysis`; included in the daily workflow. See [sources, timing and exact changed files](docs/ANALYSIS.md).

## MOS bulletin data

`/mos/` looks up original GFS MAV, NAM MET, extended GFS MEX and LAMP LAV bulletins for CONUS airports, with source/run times, raw TXT export, airport search and a reading guide. Loaded directly from IEM; no additional Actions generation job. See [MOS details and changed files](docs/MOS.md).

## REFS / GEFS ensemble probabilities

`/ensembles/` shows NOAA REFS probability products through F060 and full-31-member GEFS threshold probabilities through F384. Exact valid windows, contributing member counts, point/neighborhood distinctions and cursor readouts remain visible. Generate with `python -m ensembles`; included in the daily workflow. See [ensemble sources, definitions and changed files](docs/ENSEMBLES.md).

## El Niño / La Niña tracker

`/enso/` shows official CPC ENSO alert status, RONI/ONI history, weekly Niño 3.4 SST anomalies and the official forecast-range graphic. Generate with `python -m enso`; included in the daily workflow. Observation/issuance dates stay separate. See [ENSO data, interpretation and changed files](docs/ENSO.md).
# Radar viewer

Open `radar/index.html` through your web server for real NEXRAD Level II site data and MRMS reflectivity, rate, and precipitation accumulation. Public NOAA feeds load directly in the browser; no new credentials or scheduled job. See [radar documentation](docs/RADAR.md) for products, source attribution, build instructions, and the changed-file list.

