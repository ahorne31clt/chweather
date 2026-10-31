# Tropical outlooks

`/tropical/` covers the Atlantic, Eastern Pacific, and Central Pacific. Each basin offers the official NHC/CPHC 2-day and 7-day formation graphics, preserved unchanged, a dated outlook bulletin, and systems from NHC's active-system list. The bulletin's own RSS publication time is shown; its official nominal issuance is retained in the bulletin text and on the graphic. A feed-wide timestamp is not substituted for the bulletin's timestamp. All text is inserted safely as text. Missing feeds or invalid graphics fail the refresh instead of inventing a quiet outlook.

The default published snapshot pairs local graphics, bulletin, and system metadata. It shows when the snapshot was fetched and reminds readers to check the issuance printed on the map. An older snapshot is labeled. “Latest official graphic” attempts to load the NHC image directly and hides the stored bulletin and system list, so two issuance times are not mixed. If NHC/browser cross-site restrictions block that image, it explicitly returns to the dated snapshot and directs the reader to the official NHC link. No current conditions or probabilities are invented. Formation probabilities are not landfall or local-impact probabilities.

Sources: [NHC](https://www.nhc.noaa.gov/), [Atlantic feed](https://www.nhc.noaa.gov/index-at.xml), [Eastern Pacific feed](https://www.nhc.noaa.gov/index-ep.xml), [Central Pacific feed](https://www.nhc.noaa.gov/index-cp.xml), and [NHC current systems](https://www.nhc.noaa.gov/CurrentStorms.json).

Generate with the existing Python environment:

```sh
python -m pip install -r requirements-sunset.txt
python -m tropical
```

No required environment variables or credentials. This is a small, unattended, headless download, using the existing requests and Pillow dependencies. It saves `generated/tropical/latest.json` and six PNGs. The manifest contains generation UTC, bulletin publication times, source URLs, image sizes/hashes, and active-system metadata. It is published after all validated graphics are ready; failure exits nonzero and preserves the prior dataset.

The replacement `.github/workflows/sunset.yml` runs this command at its existing daily 8 a.m. America/New_York schedule, alongside the other outlooks and models. NHC issues updates between those site runs; use the official link for the most recent advisory. GitHub jobs can be delayed, and the full model generation takes time after the scheduled start. No new standalone workflow or secrets are required.

Changed files: added `tropical/__init__.py`, `tropical/__main__.py`, `tropical/index.html`, `assets/tropical.js`, `assets/tropical.css`, `tests/test_tropical.py`, and this document. Updated `index.html`, `outlooks/index.html`, `sunset/index.html`, `.github/workflows/sunset.yml`, `scripts/package_site.py`, `scripts/package_github.py`, and `README.md`. The ready-to-host ZIP includes the generated tropical snapshot; the GitHub source ZIP omits all generated forecasts because Actions regenerates them.
