# Independent outlook and model updates

Model rendering is now separate from the outlook workflow. Slow or failed model jobs no longer block new sunset, SPC, WPC/CPC, tropical, RTMA, ensemble, or ENSO products from publishing.

**Latest update:** products now upload and publish independently even if another job fails. The publisher collects per-product artifacts; combined bundles are no longer required. See [NDFD timing and failure-handling repair](PARTIAL-UPDATES.md) for the current update ZIP and exact changes. The three workflow names and schedules below remain the same.

## Upload the matching code and all three workflows

1. Extract `output/ch-weather-model-split-update.zip` and upload its contents to the repository root, replacing matching files while preserving folders. This contains only the files changed by this update. The complete `output/ch-weather-github-ready.zip` is also available; its smaller batch ZIPs contain fewer than 100 files each.
2. Replace `.github/workflows/sunset.yml` and add `.github/workflows/models.yml` and `.github/workflows/publish.yml`. Windows can hide `.github`; visible copies are supplied as `output/sunset.yml`, `output/models.yml`, and `output/publish.yml`. Paste their complete contents into the exact GitHub paths above. They belong inside `.github/workflows`, not at repository root.
3. Keep **Settings → Pages → Source → GitHub Actions**. Preserve the existing custom domain and `CNAME`.
4. Once all files are committed to `main`, start fresh runs of **Daily weather and sunset outlooks** and **Scheduled weather models** in Actions. Each successful completion automatically starts **Publish latest weather website**. Do not rerun an older failed run: it still uses the older code and workflow.

Direct workflow editor locations:

- https://github.com/ahorne31clt/chweather/edit/main/.github/workflows/sunset.yml
- For new files use Add file → Create new file, entering `.github/workflows/models.yml` or `.github/workflows/publish.yml` as the filename.

## The three workflows

| Workflow | Schedule | Work |
| --- | --- | --- |
| Daily weather and sunset outlooks (`sunset.yml`) | 8 a.m. America/New_York, plus 05:30 / 11:30 / 17:30 / 23:30 UTC | Seven independent product jobs. **No deterministic model generation.** Uploads each successful `forecast-PRODUCT` artifact. |
| Scheduled weather models (`models.yml`) | 05:30 / 11:30 / 17:30 / 23:30 UTC: four times daily | GFS, HRRR, and NAM run in **three separate parallel jobs**, uploading `model-gfs`, `model-hrrr`, and `model-nam` independently. GFS and HRRR include matching airport meteograms. |
| Publish latest weather website (`publish.yml`) | Automatically when either workflow completes, including failed jobs, plus manual/static-site updates | Collects each latest validated product/model artifact, falls back to previous successful artifacts for failed products, validates the site, and publishes Pages. It does not rerender models. |

Scheduled starts can be delayed by GitHub. Published model cycles are the latest complete supported cycles available when generation runs. Full ranges remain GFS 384 hours, HRRR up to 48 hours, and NAM 84 hours; no shorter GFS range or reduced parameter list was introduced to make the job appear faster. HRRR's existing explicitly labeled 18-hour fallback remains available if extended cycles cannot be used.

Each model job has 180 minutes total, with up to 150 minutes for generation; verification is a separate 40-minute job. Native ecCodes installation and Python-wheel installation have separate bounded steps. A model failure preserves that model's previous successful artifact while the other models and outlooks publish independently. Artifacts are retained for three days with their real generation/run/valid times. A product with no usable history is explicitly unavailable; publication proceeds with any validated products. If no validated artifacts exist at all, the existing deployment stays in place.

The publisher is the only workflow that deploys Pages. It serializes deployments and collects each product's newest validated artifact at publication time. Overall workflow failure does not disqualify the other jobs' successful artifacts. Extraction allows only the expected `generated/` product directories and verifies a SHA-256 digest when supplied by GitHub.

An open model page checks for new publications every five minutes and on tab return, retaining the nearest valid time. This is independent of server-side generation. Radar, satellite, warnings, local NWS forecasts, and MOS retrieve their data in the viewer.

## Local commands

```
python -m models --model gfs
python -m models --model hrrr
python -m models --model nam
```

Each command generates one model at `generated/models/` for an isolated runner; GFS/HRRR include airport data, NAM does not. Use separate checkouts/output workspaces if running these commands concurrently on your own machine. The workflows use separate Ubuntu runners. Running `python -m models` without `--model` retains the original all-three-model behavior.

`python -m scripts.merge_models --check-part generated/models --model gfs` validates a single job. `python -m scripts.merge_models --parts .model-parts --output generated/models` merges all three parts; `--allow-missing` permits independent available models. It rejects incomplete ranges, missing files, and mismatched airport runs. Incompatible airport catalogs cause the conflicting airport data to be omitted while valid model maps remain. Staging includes only referenced files.

## Environment and credentials

No user-configured secrets or API keys are needed. Publication requires `GH_TOKEN` (the workflow supplies `${{ github.token }}` automatically) and `GITHUB_REPOSITORY` (supplied automatically by Actions). The publishing workflow grants `actions: read`, `contents: read`, `pages: write`, and `id-token: write`. Never put a personal token in the source. Library setup uses `MPLBACKEND=Agg`, `PYTHONUNBUFFERED=1`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, and `TZ=UTC`; workflows set these automatically.

## Files changed

- `.github/workflows/sunset.yml`: outlook-only generation and artifact bundle; no model dependency or Pages deployment.
- `.github/workflows/models.yml`: new four-times-daily parallel GFS/HRRR/NAM workflow and model bundle.
- `.github/workflows/publish.yml`: new independent publisher triggered by either successful generation workflow.
- `models/__main__.py`: `--model` selection, model-specific cleanup, NAM skips unsupported airport generation.
- `scripts/merge_models.py`: validates, stages, and merges independent map/airport bundles.
- `scripts/collect_publication.py`: retrieves the newest successful independent bundles using GitHub's built-in token.
- `scripts/package_github.py`: includes all workflows and writes visible copies for upload.
- `tests/test_independent_publication.py`, `tests/test_packaging.py`, `tests/test_model_selection.py`: regression coverage for model isolation, complete ranges, airport merging, artifact boundaries, missing-model publication, and independent workflow wiring.
- `README.md`, `docs/REFRESHES.md`, `docs/MODELS.md`, and this guide: updated operating instructions.

Generated source/update ZIPs and visible workflow copies are in `output/`. These repairs are local until uploaded; a successful hosted run is required to verify the GitHub deployment.
