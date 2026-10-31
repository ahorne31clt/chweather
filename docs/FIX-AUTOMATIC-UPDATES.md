# Repair the automatic forecast and model updates

The GitHub repository was running the older **Daily sunset outlook** workflow. It only ran `python -m sunset`, while the uploaded website packager required generated weather, model, and airport files. Missing `generated/models/latest.json` stopped the deployment, so even successfully generated sunset images never reached the website. The repository also had no scheduled model-generation step.

## Upload this matching version

1. Extract `output/ch-weather-github-ready.zip` on your computer. Upload its **contents** to the root of `ahorne31clt/chweather`, replacing files with matching names. Do not upload the ZIP itself or create an extra enclosing folder. If GitHub limits the upload to 100 files, use the two smaller upload-batch ZIPs and upload the extracted contents of each in turn. Preserve the folders.
2. Replace **`.github/workflows/sunset.yml`** too. This is essential: ordinary uploads often omit the hidden `.github` folder. Open https://github.com/ahorne31clt/chweather/edit/main/.github/workflows/sunset.yml , select the entire old file, and paste the contents of the supplied `output/sunset.yml`. Commit to `main`. It must now be named **Daily weather and sunset outlooks** and contain `verify`, `generate`, and `publish` jobs. Keeping the old workflow leaves the same failure in place.
3. Under **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**. Your repository was also using a separate branch-based `pages-build-deployment` job; switching the source makes the forecast workflow responsible for the live deployment. Keep your existing custom-domain setting and `CNAME`.
4. Open https://github.com/ahorne31clt/chweather/actions/workflows/sunset.yml . Select **Run workflow → main → Run workflow**. This starts a fresh run with the new workflow. Do not select **Re-run jobs** on the old failed run, because that uses its older commit/workflow.
5. The run should show verification, eight product-generation jobs, and publication. Open **Generate models** for GFS/HRRR/NAM and airport progress. Open **Generate sunset** for the HRRR sunset forecast. The green **Publish website and forecasts together** step means the generated files have reached Pages. Publication is not complete when generation alone turns green.

## Automatic timing

The workflow starts at **8 a.m. America/New_York** each day, handling daylight saving time. Additional refreshes start every six hours at **05:30, 11:30, 17:30, and 23:30 UTC**. These run all eight generators so the website and model manifests stay consistent. Schedules are start times, not promises that downloads and rendering are already finished. GitHub can delay scheduled starts. Models use the latest complete supported cycle, not a partially uploaded run. HRRR extended cycles are preferred; any shorter fallback remains labeled by its actual forecast hours.

Generators run in parallel on Ubuntu (up to four at once), with up to 105 minutes for an individual generation step. Full model loops are much heavier than a single sunset map. A failed generator stays a failed job; publication requires all products to validate, so incomplete or fabricated data are never substituted. The site retains its previous successful deployment and its original timestamps on a failure.

Radar, satellite, warnings, local NWS forecasts, and MOS fetch data in the viewer; they do not wait for these scheduled rendered-map jobs. A static website cannot execute a Python model generator in a visitor's browser.

## Changes in this repair

- `.github/workflows/sunset.yml`: all eight generators, six-hour model/outlook refreshes, 8 a.m. local start, parallel jobs, generous per-job limits, complete artifact transfer and Pages publication.
- `scripts/package_site.py`: validates all required products, airport output, manifest-referenced images, smoothing overlays, and numeric lookup files; reports missing generators clearly; preserves `CNAME`; source-only enumeration works without generated data.
- `scripts/package_github.py`: source ZIP creation no longer reads generated manifests. It can run from a clean checkout before forecasts exist.
- `tests/test_packaging.py`: regression coverage for missing model/airport data, missing cursor lookup and smoothing assets, unsafe paths, clean source export, custom domains, and agreement between scheduled generators and required outputs.
- `assets/models.js` and `assets/meteogram.js`: open model pages check for new publications every five minutes and on tab return, retain the nearest valid time, and refresh airport-data caches when a new publication arrives. Updates wait until open dialogs are closed.
- `docs/REFRESHES.md`, `README.md`, and this document: corrected refresh and deployment instructions.
- Rebuilt `output/ch-weather-github-ready.zip`, `output/ch-weather-website.zip`; added `output/sunset.yml` and two smaller source-upload batches.

No credentials or manually configured environment variables are required. GitHub supplies its normal deployment token. The workflow sets `MPLBACKEND=Agg`, `PYTHONUNBUFFERED=1`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, and `TZ=UTC` for unattended rendering and bounded numerical threading.

## Check locally

After installing `requirements-sunset-dev.txt`:

```
python -m pytest -q tests
python scripts/package_site.py --check
```

To regenerate a particular product, run `python -m sunset`, `python -m weather`, `python -m tropical`, `python -m centers`, `python -m enso`, `python -m analysis`, `python -m ensembles`, or `python -m models`. Check it with `python scripts/package_site.py --check --product models` (substitute its product name). Once all outputs exist, `python scripts/package_site.py --output-dir _site` builds the public folder. `_site` must be a fresh directory; the packager intentionally refuses to delete existing folders.

The local repair and tests do not prove that a new run has succeeded on GitHub. That requires uploading the matching workflow and sources and starting the fresh run above.
