# Exact project-file changes: sunset forecast and About headshot

Paths below are relative to the `CHWeather Site` workspace folder.
This list covers the sunset forecast request and the headshot follow-up.

## Existing project files modified

| File | Change |
| --- | --- |
| `.gitignore` | Exclude the virtual environment, download cache, test cache, and `_site` export. |
| `README.md` | Add the command, output paths, setup-document link, and publication status. |
| `build_site.py` | Keep initial generation consistent with the headshot, homepage outlook section, and Sunset Outlook link. |
| `index.html` | Add Sunset Outlook navigation, homepage forecast section, and metadata loader; adjust the placeholder wording. |
| `portfolio/about.html` | Replace the large profile logo with the supplied square headshot; retain other logo placements. |
| `assets/styles.css` | Add headshot, forecast image, timestamps, stale notice, and responsive highlight styles. |
| `output/ch-weather-website.zip` | Refresh the static website export with the headshot, sunset page, documentation, and current generated outputs. |

## New project files

| File | Purpose |
| --- | --- |
| `.github/workflows/sunset.yml` | Daily 08:00 America/New_York Ubuntu generation, tests, artifacts, and GitHub Pages deployment. |
| `requirements-sunset.txt` | Pinned direct runtime dependencies. |
| `requirements-sunset-dev.txt` | Runtime dependencies plus pinned pytest. |
| `sunset/__init__.py` | Python package. |
| `sunset/__main__.py` | One-command orchestration, metadata, validation, and staged output writes. |
| `sunset/data.py` | Bounded NOAA downloads, instantaneous GRIB decoding, cycle fallback, and map boundaries. |
| `sunset/model.py` | Sunset geometry, time interpolation, sunward sampling, potential score, and separated maxima. |
| `sunset/render.py` | Headless 2400 × 1500 branded filled-contour graphic. |
| `sunset/cities.json` | Geographic reference cities for the three actual grid maxima. |
| `sunset/index.html` | Dedicated forecast page, sources, method, and limitations. |
| `assets/christopher-horne-headshot.png` | Unchanged copy of the headshot supplied by Christopher. |
| `assets/sunset-section.html` | Shared generation template for the homepage forecast section. |
| `assets/sunset.js` | Fetch JSON, display timestamps and highlights, and label stale/missing forecasts. |
| `scripts/package_site.py` | Allowlisted static directory/ZIP export used locally and in Actions. |
| `tests/test_sunset.py` | Ten numerical, data-integrity, separation, and failure-path checks. |
| `docs/SUNSET.md` | Exact Ubuntu setup, scheduling/hosting steps, environment variables, formula, primary sources, and limitations. |
| `docs/CHANGES-SUNSET.md` | This exact change list. |
| `generated/sunset/latest.png` | Real-data forecast graphic from the latest successful local run. |
| `generated/sunset/latest.json` | Run, valid date, generation UTC, filename/hash, source URLs, and location metadata. |

## Local verification artifacts (not part of the source or published website)

- `.venv/`: local Python environment.
- `.cache/sunset/`: NOAA GRIB subsets and Natural Earth downloads.
- `.pytest_cache/` and Python `__pycache__/` directories: test/import caches.
- `_site/`: allowlisted copy of the website used for local preview and deployment.

These temporary directories are ignored by Git. The original CH Weather logo,
social-media embeds, résumé PDF, and other portfolio pages were not changed by
this request. No repository push, live-site deployment, or remote schedule was
activated; GitHub setup is documented in `docs/SUNSET.md`.
