# Update note

For the newer experimental profile-diagnosed type map, added parameters, RRFS/ECMWF adapters and compact publication graphics, see SEVERE-WINTER-AND-NEW-MODELS.md. The measurements below describe the initial eight-parameter integration.

# WOOF-NAM integration and model scaling

## Source findings, checked November 5, 2026

Source: https://woof-nam.recastsystems.com/README.txt
Inventory/status: https://woof-nam.recastsystems.com/status.json
Compatibility: https://github.com/recastsystems/woof-nam/blob/main/docs/COMPATIBILITY.md

WOOF-NAM by Recast is a separate NAM-style 12.19 km North American model, not a continuation of NOAA's operational NAM. Its announced public pilot is November 5 06Z through November 12 00Z, 2026. Runs are scheduled at 00/06/12/18Z to F084, with a seven-day retention period. Availability after the pilot is not promised. Credit: WOOF-NAM by Recast, CC BY 4.0. Headers use NCEP parameter tables but generating process 254; they do not establish NOAA authorship.

The adapter selects complete compatible recent cycles using status.json, requests bounded GRIB messages through .idx inventories and HTTP 206 Range, checks exact response lengths, grid, field units, run and valid times, and generating process. Pre-November-5-06Z layouts are excluded. Twelve fields yielded 2,638,687 downloaded bytes for F024 rather than its roughly 66.4 MB full file. Adjacent selected messages are combined into fewer requests.

Published products: 2m temperature, 2m dewpoint, 2m relative humidity, 10m wind, MSLP, surface CAPE, 500mb heights/wind, 500mb absolute vorticity. F000-F084 every three hours (29 frames). Missing precipitation type, instantaneous rate and accumulated snow are not manufactured. Rate meteograms remain GFS/HRRR only. APCP exists but requires a separate interval-aware accumulation implementation, including 12-hour resets; it is not treated as instantaneous rate.

## Run and install

Existing requirements-sunset.txt and ecCodes installation remain sufficient. No new environment variables or credentials.

    python -m pip install -r requirements-sunset.txt
    python -m models --model woofnam --workers 2

The existing Scheduled weather models workflow has an independent woofnam matrix job. The publisher restores model-woofnam artifacts alongside GFS and HRRR. WOOF failure does not prevent the other models publishing. After uploading, run Scheduled weather models; Publish latest weather website follows automatically. A complete cycle must finish before this model is published. Old completed artifacts can remain with their original dates when a refresh fails.

## Efficiency implemented

The viewer already used pre-rendered static images; no browser GRIB decoding was needed. New frames now select lossless WebP only when smaller than PNG. This preserves the already-rendered pixels and does not change raw cursor values. A tested WOOF F024 temperature frame was 164,134 bytes WebP versus 519,909 bytes optimized PNG: 68.4% smaller for that frame, not a universal guarantee.

A bounded browser Cache API stores up to 48 hash-versioned map responses across visits, with an eight-image in-memory working set and neighboring-frame prefetch. Disabled/full storage falls back to ordinary browser caching. Numeric probes remain separate compressed data. New images may still have a cold-network loading delay. Cache is origin-local and contains public map graphics only.

## Architecture for more models and parameters

models/catalog.py centralizes model identity, horizon, cadence, source credit and airport capability; the publication collector iterates this catalog. The viewer discovers available model identities from the manifest instead of a GFS/HRRR allowlist and accepts PNG/WebP graphic references. models/fields.py remains the parameter catalog. Adding a source still requires a source adapter and validated scientific field mappings; adding a parameter still requires an explicit recipe, units, legend and tests. Metadata alone does not invent a calculation.

Recommended next stages:
1. Separate immutable run manifests from the small latest-run index, avoiding repeated large JSON fetches.
2. Reuse a completed render bundle when run, source checksums, parameter recipe and renderer version all match. Do not reuse merely because the date matches.
3. Split large generation jobs by model/run/parameter group, with bounded concurrency and a validated final merge. Download source fields once per group, not once per image.
4. Retain native numerical data once, and derive multiple graphics from it. Keep probes independent of display resolution.
5. Introduce lower-resolution previews plus full-resolution downloads; only fetch full images when needed.
6. Use tiles for deeper zoom, with projection-aware numerical queries, once a full-frame viewer becomes too expensive.
7. Move bulk graphics to object storage/CDN before expanding run history and model counts. Keep GitHub Pages for the HTML/CSS/JS.
8. Set per-model horizons, cadence and parameter groups explicitly, with a storage/build-time budget and measured performance.

GitHub Pages published sites are limited to 1 GB; simply multiplying full images by models, parameters and stored runs will not scale indefinitely. Source: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits . WebP background: https://developers.google.com/speed/webp/docs/webp_lossless_alpha_study .
