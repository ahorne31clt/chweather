# CH Weather model room

Open `/models/`. This is a plain HTML/CSS/JavaScript viewer of graphics generated from real NOAA/NCEP numerical model output. The map fills the available width, with compact controls below it. Select GFS/HRRR/NAM and a map field, then use the timeline, previous/next, playback speed, arrow keys, space, zoom/drag, Fit, fullscreen, and PNG download. The Map guide explains the fields. Times on the graphics are always UTC; the control bar also offers Eastern time.

## Data and fields

- **GFS:** NOAA NOMADS 0.25-degree GRIB filter, CONUS subset, forecast hours 0–384 every 3 hours (129 frames), covering the full 16-day run. The published cadence stays at three hours throughout.
- **HRRR:** NOAA NOMADS 2-D surface-file GRIB filter, native 3 km CONUS grid, hours 0–48 hourly (49 frames) from 00/06/12/18 UTC extended cycles. If no complete extended cycle is available, the viewer explicitly falls back to a recent 0–18-hour sequence (19 frames). Precipitation pixels retain the model grid; the rendered PNG is 2400 × 1350.
- **NAM:** NOAA 12 km CONUS pressure-level grid, F000-F084 every three hours (29 times). Eight parameters are published; instantaneous precipitation rate/type and airport rate meteograms are unavailable because this feed does not provide the PRATE field used by those products. No substitute is fabricated.
- **New surface fields:** 10 m sustained wind speed/barbs in knots, native model 2 m relative humidity in percent, standalone mean sea-level pressure in hPa with 4-hPa contours and H/L centers, and surface-based CAPE in J/kg. CAPE uses the surface parcel, not a mixed-layer or most-unstable parcel, and is not a probability of severe weather. These use actual UGRD/VGRD, RH, PRMSL/MSLMA, and surface CAPE model fields.
- **Precipitation type:** instantaneous CRAIN, CSNOW, CFRZR, and CICEP categorical flags. A single active flag identifies rain, snow, freezing rain, or sleet. Multiple flags are labeled mixed; a rate without a type flag is unclassified. No category is inferred from thickness. This is a categorical field, not a precipitation-type probability.
- **2 m temperature / dewpoint:** separate Fahrenheit maps from instantaneous TMP/DPT at 2 m above ground. City labels and the denser evenly spaced CONUS land-value readouts use the nearest native grid point. Hover or tap for both values; these readouts sample the native fields onto an 4-image-pixel display grid (roughly 10 km in this national view), not exact-address conditions. Maps and values share the same initialization and valid time. A city value and nearby pointer sample can differ because they sample different native grid points.
- **500 mb heights + wind:** wind speed is `sqrt(UGRD^2 + VGRD^2) * 1.94384449244` knots, with height contours every 6 dam. Wind barbs show direction and speed in knots (half-barb 5 kt, full barb 10 kt, flag 50 kt); winds below 5 kt are omitted. GFS uses earth-relative vectors transformed from longitude/latitude; HRRR grid-relative vectors are drawn in its native Lambert projection. GRIB vector-orientation flags are validated. Speed shading remains invariant to vector rotation.
- **500 mb absolute vorticity:** the model-supplied ABSV field, multiplied by 100,000 and labeled in 10^-5 s^-1; this includes planetary rotation and is not relative vorticity. Heights are overlaid every 6 dam. HRRR uses its pressure-level file: a public NOAA archive index identifies the single 500 mb ABSV byte range. The downloader requires an exact HTTP 206 range response rather than loading the full pressure-level file.
- **Rate shading:** instantaneous PRATE × 3600, in liquid-equivalent mm/hour. Values below 0.1 mm/hour are not shaded. Brightness bands have boundaries 0.5, 2, 5, 10, and 20 mm/hour. This is not accumulated rainfall or snowfall depth.
- **Solid contours:** mean sea-level pressure every 4 hPa, using GFS PRMSL or HRRR MSLMA (MAPS-system reduction). This interprets the requested surface-pressure display as the standard meteorological map product, not station pressure over terrain.
- **Dashed contours:** (500 mb geopotential height − 1000 mb geopotential height) / 10, every 6 decameters. This interprets “500 mb thickness” as standard 1000–500 mb thickness. Cold-side contours through 540 dam are blue sage; warmer contours are gold. Thickness alone does not determine precipitation type. The 1000 mb level can be below terrain.

**Pressure symbols:** blue H and red L identify selected broad closed extrema in mean sea-level pressure, with rounded smoothed hPa values below. Both models are sampled on the same approximately 35 km projected analysis grid and smoothed at a 75 km Gaussian scale. A center must be an extremum within 250 km, with at least 0.75 hPa of change in every direction on a 280-350 km ring. Missing neighborhoods, map-edge centers, and open gradients are excluded. Markers are at least 600 km apart, with at most five of either kind. This is an automated display heuristic, not an official surface analysis; it can omit weak or elongated systems.

For readable contours, GFS pressure/thickness fields receive Gaussian smoothing of 0.6 grid cells; HRRR contours receive 3 grid cells and are drawn at every fourth grid point. Precipitation categories, temperature, dewpoint, and wind-speed shading are not smoothed. Upper-air height contours use the same contour smoothing. Absolute-vorticity shading is Gaussian-smoothed at 1 GFS grid cell or 5 HRRR grid cells (about 15 km). Surface maps include fixed colorbars in Fahrenheit; wind maps use knots and height contours use decameters. PNG palette optimization reduces file sizes without changing the numerical readout files. Boundaries are Natural Earth. Forecast guidance can differ from observations and official forecasts.

References: [NOAA GFS forecast cadence](https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs.php), [NCEP HRRR extended-cycle schedule](https://www.nco.ncep.noaa.gov/pmb/products/hrrr/), [NOAA thickness charts](https://www.noaa.gov/jetstream/upper-air-charts/constant-pressure-charts-thickness), [NOMADS](https://nomads.ncep.noaa.gov/), [HRRR surface-file inventory](https://www.nco.ncep.noaa.gov/pmb/products/hrrr/hrrr.t00z.wrfsfcf02.grib2.shtml), [HRRR pressure-level inventory](https://www.nco.ncep.noaa.gov/pmb/products/hrrr/hrrr.t00z.wrfprsf02.grib2.shtml), [GFS inventory](https://www.nco.ncep.noaa.gov/pmb/products/gfs/gfs.t00z.pgrb2.0p25.f003.shtml).

## Install and generate

Ubuntu / GitHub Actions, Python 3.12:

```sh
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends libeccodes0
python -m pip install -r requirements-sunset.txt
python -m models
```

The single final command downloads, validates, calculates, and renders both model sequences without prompts or windows. **No credentials or required environment variables.** Dependencies are shared with the existing sunset/weather pipeline. Public NOAA endpoints can be temporarily unavailable.

For a small preview only:

```sh
python -m models --gfs-end 6 --gfs-step 3 --hrrr-end 2 --hrrr-step 1
```

This publishes only those six frames. Run the default command again for the full 207 forecast times: 9 parameters for GFS/HRRR and 8 for NAM (1,834 PNGs) when extended HRRR is available. GFS end hour must be divisible by its step (3, 6, or 12); HRRR step choices are 1, 2, 3, or 6. Maximum ends are 384 and 48 respectively; `--nam-end` accepts multiples of 3 through 84.

The generator considers three recent GFS cycles. For HRRR requests beyond 18 hours, it first considers three recent 00/06/12/18 UTC cycles, each for the complete requested extended horizon. Only if all three fail does it try three recent hourly cycles through 18 hours. It allows four hours for GFS dissemination and two for HRRR. This favors the latest complete extended HRRR run over a newer short hourly run. The actual initialization and last forecast hour remain visible; the viewer explicitly labels an 18-hour fallback.

The final required hour is probed before downloading a whole sequence. A model with no complete usable sequence is explicitly marked unavailable if the other model succeeds. If neither succeeds, the command exits nonzero and keeps the previous publication. Runs and valid times are checked against GRIB headers. No weather is invented. Sequential filtered requests, disk caching under `.cache/models`, and pauses keep the job modest: approximately 1.5 GB of filtered GRIBs and 700 MB of website assets including airport guidance for the full sequences, with actual sizes varying by weather. Two render processes are used by default, with at most two frame jobs in flight. Use `--workers 1` for a small local machine. No desktop rendering is used. The workflow allows 45 minutes for model generation and 60 minutes overall; normal operation should finish sooner. Failed candidates can take longer because public downloads are retried.

Output:

```text
generated/models/latest.json
generated/models/gfs-YYYYMMDDHH-fFFF.png
generated/models/hrrr-YYYYMMDDHH-fFFF.png
generated/models/{model}-YYYYMMDDHH-fFFF-temp2m.png
generated/models/{model}-YYYYMMDDHH-fFFF-dewpoint2m.png
generated/models/{model}-YYYYMMDDHH-fFFF-wind500.png
generated/models/{model}-YYYYMMDDHH-fFFF-vort500.png
generated/models/{model}-YYYYMMDDHH-fFFF.bin
```

The schema-2 manifest includes five product definitions, per-frame image maps and hashes, readout metadata/hashes, HRRR vorticity source URLs, and generation UTC, per-model initialization, resolution, requested/actual end hour, extended-run status, available hours, per-frame valid UTC/source URL/image/hash, and field/interval definitions. It is written after all selected images. The viewer requests only the selected and neighboring images, rather than downloading the whole animation up front. Missing images or metadata produce an explicit error. Readout failures leave the map and printed city values available, with an explicit readout error.

Readouts now cover every parameter. Per-frame `.bin.gz` files contain quantized signed 32-bit integers on a 600 x 337 display grid (4 image pixels per sample). Each field has its own unit and display precision in `field_specs`. Physical values equal integer / 10^decimals; -2147483648 denotes missing. Each field is row-major; horizontal differences are stored modulo signed 32-bit arithmetic, then gzip-compressed. Reconstruct each row with cumulative signed-32-bit addition before interpreting the values. The browser checks SHA-256 and byte count, decompresses using DecompressionStream, and retains only a few decoded frames. All values come from the underlying model fields, never by sampling image colors.

Temperature/dewpoint are rounded to 0.1 F, wind to 0.1 kt, humidity to 0.1%, pressure to 0.1 hPa, heights/thickness to 0.1 dam, absolute vorticity to 0.1 x 10^-5 s^-1, CAPE to 1 J/kg, and precipitation rate to 0.01 mm/hour. Precipitation type is the model categorical classification, including unclassified/mixed flags. Missing values display as missing.

The Native/Smooth selector interpolates and softly filters only the color field. A separately rendered transparent annotation layer preserves sharp labels, boundaries, contours, and barbs. Smoothing does not add native forecast resolution or modify pointer values. It is disabled for categorical precipitation-type maps. Smoothed PNG downloads include a display-smoothing label. New frame/model selections cannot show old values while downloads finish. Modern browser gzip-stream support is needed for these compressed readouts.

## Automatic publication and GitHub upload

The existing `.github/workflows/sunset.yml` now runs `python -m models` after the other outlooks and includes the generated images in the Pages deployment. Its existing 8 a.m. America/New_York schedule, manual Run workflow button, and relevant pushes all regenerate and publish the website together. The models update on that schedule; they do not fetch a new run every time a visitor opens the page. Check Init and Valid. GitHub scheduled jobs may start late. No new repository secrets or paid services are required. The extra downloadable artifact retains sunset/weather maps and model/airport metadata for one day. The larger model images and airport buckets are included in Pages rather than duplicated in that artifact.

Use `output/ch-weather-github-ready.zip` for source upload: **extract it first and upload the contents with folders intact**, merging/replacing matching files at the repository root. Keep the existing CNAME. Replace the existing workflow with the included `.github/workflows/sunset.yml`; if browser upload hides `.github`, open that exact file on GitHub, click Edit, and paste its replacement contents. Generated model PNGs, binary samples, and the model manifest are deliberately excluded from the source ZIP; the workflow generates them. Keep GitHub Pages → Source set to GitHub Actions, then Actions → Daily weather and sunset outlooks → Run workflow. Wait for the deployment to finish and open `/models/`.

For a static export containing the already-generated images, use `output/ch-weather-website.zip`, or run `python scripts/package_site.py --zip output/ch-weather-website.zip`. The GitHub source ZIP is rebuilt with `python -m scripts.package_github`.

## Airport meteograms

Use the Meteogram button in the viewer to search more than 15,000 CONUS airports and plot the selected GFS/HRRR run. `python -m models` now also generates these airport datasets after rendering maps. To refresh airport guidance alone from the existing model publication/cache, use `python -m models.airports`. See [airport setup and data format](AIRPORTS.md). There are no added credentials or required environment variables.

## Viewer navigation improvements

Region presets (CONUS, Carolinas, Southeast, Northeast, Plains, West) crop and zoom the existing national graphic, with a pinned color key. They do not create a finer weather grid. Cropping centers are projected separately for each model, rather than using the same pixel position for all projections. Wind vectors respect GRIB earth/grid-relative orientation. NAM uses its 12 km native Lambert grid; GFS and HRRR resolutions are unchanged.

Changing models selects the nearest available UTC valid time and reports when no exact match exists. A parameter absent from the new model is disabled; the viewer labels its fallback parameter. Tools / guide includes loop start/end selectors, a forecast-hour jump, and Copy link. Left/right arrows step within the selected loop; Home/End choose its bounds and Space plays/pauses. The main slider can still inspect any published hour. Shared URLs preserve model, parameter, run identifier, forecast hour, region or custom zoom, time zone, and loop bounds. Only current published cycles are retained: if a shared run has been replaced, the viewer explicitly reports that it is showing the latest cycle.

NAM source: [NCEP NAM product inventory](https://www.nco.ncep.noaa.gov/pmb/products/nam/nam.t00z.awphys06.tm00.grib2.shtml). Surface/convective parameters are fetched as separate bounded GRIB subsets and validated for units, level, initialization, lead, grid, and valid time. GRIB multi-field support decodes NAM's paired U/V records.

## Viewer-only asset refresh

`python -m models.viewer_assets` regenerates universal probes and annotation layers from the currently published runs and their model cache without selecting a newer cycle. `--probes-only` updates only the compact numeric data. Normal `python -m models` now produces both automatically.
# Independent scheduled model runs

`.github/workflows/models.yml` generates GFS, HRRR and NAM in three parallel jobs at 05:30, 11:30, 17:30 and 23:30 UTC. Each uses `python -m models --model gfs` (or `hrrr` / `nam`), preserving the full forecast range and all supported parameters. GFS/HRRR airport data is generated within its matching job. These runs do not block the separate outlook workflow. The dedicated publisher combines each latest validated model and outlook artifact. See [workflow setup](FIX-AUTOMATIC-UPDATES.md). The original `python -m models` command still generates all three models locally.

