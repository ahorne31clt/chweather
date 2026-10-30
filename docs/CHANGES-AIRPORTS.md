# Airport meteograms and map refinements

Added:
- `models/airports.py` — catalog, actual model sampling, 10 m wind downloads, bucket publication, and standalone command.
- `assets/meteogram.js` — local airport search, model charts, time selection, map linking, PNG/CSV exports, and verified bucket loading.
- `assets/meteogram.css` — responsive dialog and chart styling.
- `tests/test_airports.py` — nearest sampling, missing/outside-grid handling, field units, and surface wind calculation.
- `docs/AIRPORTS.md` and `docs/CHANGES-AIRPORTS.md`.
- `generated/models/airports/latest.json`, `catalog.json`, and timestamped GFS/HRRR binary buckets — generated data, not source-upload files.

Changed:
- `models/index.html` — Meteogram button/dialog and updated map guide.
- `assets/models.js` — current-run coordination, pause/keyboard integration, and 4-pixel readout support.
- `models/__main__.py` — automatic airport generation after maps, updated sample-grid note.
- `models/data.py` — 10 m wind selection and 500 mb vector-orientation validation.
- `models/render.py` — dark boundaries, denser values with city-label spacing, finer pointer samples, and 500 mb wind barbs.
- `models/fields.py` — wind-barb legend.
- `scripts/package_site.py` — include only published airport assets.
- `.github/workflows/sunset.yml` — keep larger model/airport assets in Pages while retaining only smaller outlooks and metadata in the extra artifact.
- `README.md`, `docs/MODELS.md`, `docs/CHANGES-MODELS.md` — current features and setup.

Regenerated `generated/models/` maps/readouts, refreshed `_site/`, and rebuilt `output/ch-weather-website.zip` and `output/ch-weather-github-ready.zip`. No new dependencies or required environment variables. `_site/` and development files under `output/` are local previews/work files; upload the extracted source ZIP contents to GitHub.
