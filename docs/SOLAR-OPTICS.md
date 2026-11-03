# Solar-optics favorability: class research prototype

Open `/optics/`. Six phenomena have CONUS and North Carolina contour maps:
22-degree halos, sundogs, circumzenithal arcs, circumhorizontal arcs, upper
tangent arcs, and rainbows. The map is the maximum sampled ingredient score
over the next 24 hourly samples, not a simultaneous display forecast. A city
table gives the individual hours, solar elevations, best modeled window,
model inputs, and a downloadable observation worksheet.

## Science and references

- [NWS: halos, sundogs and pillars](https://www.weather.gov/arx/why_halos_sundogs_pillars):
  ice-crystal refraction/reflection and the importance of crystal orientation.
- [NWS: rainbows](https://www.weather.gov/fgz/Rainbow): liquid droplets opposite
  the Sun, approximately 42-degree primary-bow radius, and the ground-observer
  solar-elevation restriction.
- [Hong Kong Observatory: circumhorizontal arc](https://my.weather.gov.hk/en/education/weather/clouds/00499-circumhorizontal-arc.html):
  horizontal plate crystals, Sun above approximately 58 degrees and strongest
  geometry near 68 degrees. This is not a fire rainbow.
- [WMO: circumzenithal arc](https://cloudatlas.wmo.int/en/circumzenithal-arc.html):
  near-zenith arc and geometry near 22-degree solar elevation.
- [Bureau of Meteorology: halos](https://media.bom.gov.au/social/blog/1917/explainer-what-are-halos/):
  plate and column crystal orientation, tangent arcs and the below-32-degree
  circumzenithal limit.
- [NOAA GFS variable inventory](https://www.nco.ncep.noaa.gov/pmb/products/gfs/gfs.t00z.pgrb2.0p25.f003.shtml):
  available physical model fields and units.

These references establish optical physics, not the forecast index's validity.
All weights, thresholds, distance choices and temporal aggregation below are
unvalidated CH Weather research heuristics. No numerical forecast skill or
occurrence probability is claimed. Different phenomena's numerical scores are
not calibrated for comparison with each other.

## Inputs and reproducible recipe

NOAA/NCEP GFS 0.25-degree subsets cover 132–62 W, 20–54 N, including viewing-ray
padding. Only the following fields are downloaded, every three forecast hours:
low/middle/high cloud fraction, visibility, total precipitation rate, categorical
rain flag, and temperature, published relative humidity and cloud ice mixing ratio
at 300/400/500 hPa. Units, run, forecast time, instantaneous interval, missing
values, grid scan and spacing are validated. Pressure levels are not fixed heights.

The latest candidate run is at least five hours old to allow publication; two
older six-hour cycles may be attempted. Failed/incomplete cycles are never mixed.
Nine or ten small subsets normally cover the next 24 hourly samples. Inputs are
linearly interpolated between their three-hour samples. Geometry uses NOAA
fractional-year equations through the existing solar-altitude utility; it is
adequate for this coarse heuristic, not precision ray-traced optics. All times
and run identifiers are retained in UTC. The browser can display UTC or the
viewer's own browser time zone; that zone is not automatically the selected city's.

For each level, define `cold = clip((263.15 - T_K)/20, 0, 1)`,
`moist = clip((RH_percent - 50)/40, 0, 1)`, and
`ice = 1 - exp(-max(ICMR_kg_per_kg, 0)/0.00001)`.
The crystal-environment proxy is the maximum across levels of
`cold * (0.4 * moist + 0.6 * ice)`.
Published model RH is not relabeled as relative humidity over ice or as observed
ice supersaturation. Cold, moist modeled air does not establish crystal habit.

Let `h` be high-cloud fraction, `l` low and `m` middle fractions.
The veil proxy is `sqrt(h) * (1 - 0.55*h^3)`; the unobscured-sky proxy is
`(1-l)*(1-0.8*m)`. Visibility contributes `clip(VIS_m/15000,0,1)`.
Multiply this visibility factor by the square root of unobscured-sky proxy at
the observer times the same proxy sampled 40 km toward the Sun. The base
ice-optics score is 100 times this viewing factor, veil proxy and
crystal-environment proxy. These horizontal samples are a simple obstruction
proxy, not cloud-height-aware radiative transfer.

- Halo: base score with Sun above zero degrees.
- Upper tangent arc: same ingredient score. The model cannot resolve the column
  orientation distinguishing this phenomenon from a halo. No independent
  prediction is fabricated.
- Sundog: base times `0.25 + 0.75*exp(-((elevation-12)/25)^2)` for daylight.
  Low Sun is favored, but 32 degrees is not incorrectly used as a sundog cutoff.
- Circumzenithal: base times `exp(-((elevation-22)/14)^2)`, only 0–32 degrees.
- Circumhorizontal: base times `exp(-((elevation-68)/18)^2)`, only above 58 degrees.
- Rainbow: total precipitation rate is converted to mm/hour and multiplied by
  the categorical rain flag (a fraction after interpolation). Its maximum is
  sampled 10/25/40 km away in three antisolar directions: center and ±0.35 radians.
  Score is `100*(1-exp(-nearby_liquid_rain_mm_h/0.5))*viewing_factor`, only with
  Sun between 0 and 42 degrees. A real bow spans a much wider cone; this is a
  nearby-rain ingredient search, not a simulation of the complete bow.

No ice-shape, crystal alignment, optical depth, droplet-size spectrum, diffraction,
terrain, buildings, aerosols or three-dimensional scattering is simulated. Small
showers and broken clouds can be missed. Very cold surface diamond dust is not
explicitly modeled. Coronas, glories, iridescence and rare halo arcs are not
separately forecast because the necessary particle/microphysical information is
missing. Above-ground or mountain viewpoints can invalidate the ground-observer
rainbow restriction. The CONUS map is a regional ingredient guide, not a
street-level observing recommendation. North Carolina is a crop of the same
native grid, not a higher-resolution model.

## Run locally or unattended on Ubuntu

Python 3.12 and the existing dependencies suffice. No new dependency or credential
is required. No required environment variables. `MPLBACKEND=Agg` is recommended
and is already set by the workflow; the renderer also selects Agg explicitly.

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends libeccodes0
python -m pip install --only-binary=:all: -r requirements-sunset-dev.txt
python -m pytest -q tests/test_optics.py
MPLBACKEND=Agg python -m optics
python scripts/package_site.py --check --product optics
```

One command, `python -m optics`, fetches, calculates and renders. Failure exits
nonzero; no sample weather is substituted. Outputs are staged and the manifest
is replaced last. Source cache files older than four days are pruned.

Output: `generated/optics/latest.json`, `locations.json`, and twelve PNG files.
The manifest includes model run, forecast valid date, valid window, UTC generation
time, image filenames/hashes, every input URL, scientific references, geometry
and data intervals, algorithm version and limitations. The location JSON includes
hourly scores, solar elevations and actual sampled input fields. The default
minimum/maximum time window is rolling UTC, not local midnight-to-midnight.

## GitHub upload and automation

Extract `output/ch-weather-solar-optics-update.zip`. Upload its contents into
the repository root, retaining directories, and replace matching paths. Include
the hidden `.github/workflows/sunset.yml` file in its proper directory.

Run **Daily weather and sunset outlooks** once. Its new independent `optics`
matrix job runs `python -m scripts.run_product optics`, validates references and
uploads `forecast-optics`. The existing publisher discovers it automatically.
Other successful families still publish if optics fails. The existing 8 a.m.
New York and additional scheduled outlook refreshes include optics; no extra
workflow or secrets are required. Until the first successful artifact, the page
states that guidance is unavailable. The publisher can retain an earlier
successful artifact, and the page labels stale valid times.

## Observation plan for class

Use **Download observation worksheet** after selecting a city and phenomenon.
The CSV has UTC times, model run, score, Sun elevation, and empty observation,
cloud-note and photo-reference fields. It downloads locally; nothing is sent
to a server. Record clear non-detections and periods when you could not observe,
not just successful sightings. Observation opportunity and viewing obstruction
must be distinguished from an actual atmospheric non-event. A later independent
time-blocked evaluation can test useful score thresholds, false alarms and
missed events; the prototype has not undergone that evaluation.

Never look directly at the Sun. Keep it safely behind a solid obstruction and
do not scan near it with binoculars or a telescope. Do not approach storms to
observe rainbows.

## Exact source files added or replaced

Added: `optics/__init__.py`, `optics/data.py`, `optics/science.py`,
`optics/render.py`, `optics/__main__.py`, `optics/index.html`,
`assets/optics.js`, `assets/optics.css`, `tests/test_optics.py`, this guide.

Replaced: `assets/navigation.js`, `outlooks/index.html`,
`.github/workflows/sunset.yml`, `scripts/package_site.py`,
`scripts/package_github.py`, `README.md`.

Generated forecast files are rebuilt by Actions and need no manual GitHub source
upload. Local preview copies are also updated under `_site/`.

## Version 2: HRRR refinement and GOES context

The current default first computes the GFS-only ingredients, then replaces low,
middle and high cloud fractions and visibility with **hourly HRRR** values where
all four inputs are available. Extended 00/06/12/18 UTC runs must reach the entire
24-hour window within their 48-hour forecast horizon. Both model runs and their
individual source URLs are recorded. The existing strict HRRR decoder validates
3 km grid geometry, units, model initialization, lead and missing data. Each
native HRRR field is sampled onto the 0.25-degree optics grid. This is NOT a full
3 km optics map: GFS still supplies 300/400/500 hPa temperature, humidity, cloud
ice and rain. Mixed-model cloud/ice consistency is an additional uncertainty.
Where the HRRR projection does not cover a padded ray point, the original GFS
field is retained and coverage is recorded. If no complete HRRR run exists,
GFS-only guidance is published with an explicit unavailable status. Higher
resolution does not prove higher optics skill.

The location JSON preserves `gfs_scores` alongside the displayed refined scores.
The city panel exposes the comparison at its best sampled hour. This difference
is model disagreement, not confidence or verified improvement. The original
three-hour-input limitation now applies to the GFS profile and rain fields;
HRRR clouds and visibility and solar geometry are hourly.

GOES-19 and GOES-18 Band 4 (1.37 micrometer daytime cirrus) and Band 13 (10.3
micrometer infrared context) are downloaded as independent observed snapshots.
Only actual timestamped NOAA frames matching the requested satellite/channel
are accepted, at most two hours old during generation (up to ten minutes future
clock tolerance). Latest matching frames are selected, never guessed URLs.
Images are bounded to 8 MB per download, checked with Pillow and saved as PNG.
Their timestamps, source URLs, missing-channel failures and descriptions are in
the manifest. Older snapshots are visibly labeled in the browser; the existing
satellite viewer provides fresher context between scheduled outlook refreshes.

Band 4 is useful for thin cirrus during DAYLIGHT; a dark night image does not
mean clear sky. Infrared is not a crystal-habit measurement. Satellite snapshots
are **not assimilated into the score**, and a single observed cloud image is not
extrapolated over a 24-hour forecast. Implementing a quantitative nowcast would
require cloud motion, phase/optical-depth retrievals, quality flags and independent
verification. See NOAA's [Band 4 quick guide](https://www.star.nesdis.noaa.gov/GOES/documents/ABIQuickGuide_Band04.pdf).

No new dependencies, secrets, command or workflow are required. HRRR downloads
are bounded, decoded one lead at a time, and only small sampled fields are kept;
24 forecast hours normally add at most 480 MB of bounded downloads (usually much
less). Local caches older than four days are pruned. Satellite failure is
reported separately and does not fabricate observations or invalidate an
otherwise complete model forecast.

The page now shares `collection.css`, the outlook collection's tab buttons,
region-button styling, 1320 px layout, typography and sharp-edged controls.
The observation worksheet button explicitly uses the site's dark styling.

Additional v2 files: `optics/context.py` and `tests/test_optics_context.py`.
Changed for v2: `optics/__main__.py`, `optics/render.py`, `optics/index.html`,
`assets/optics.js`, `assets/optics.css`, `scripts/package_github.py`, this guide.
The update ZIP includes all original optics integration files so it can replace
version 1 without deleting unrelated repository files.
