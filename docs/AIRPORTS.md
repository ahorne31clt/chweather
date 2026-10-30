# Airport meteograms

Open `/models/`, select GFS or HRRR, and click **Meteogram**. Charlotte (KCLT/CLT) is the initial airport. Search by ICAO, IATA, local identifier, airport name, or city and select a result. The catalog includes more than 15,000 small, medium, and large US airports within the CONUS map domain; heliports, closed airports, Alaska, Hawaii, and territories outside that domain are excluded.

The interactive chart uses the same initialization and forecast hours as the selected model map: GFS through F384 every three hours, and HRRR through F048 hourly when an extended run is available. An 18-hour fallback charts only its actual published hours. The airport model selector also changes the model on the map. Move/tap on the chart or use its keyboard-accessible time slider to inspect a forecast time. **View this hour on map** closes the dialog at that hour. PNG and CSV downloads contain the actual displayed model series and initialization.

## Meteorological fields

- 2 m temperature: instantaneous TMP, converted from kelvin to Fahrenheit.
- 10 m sustained wind: `sqrt(UGRD² + VGRD²) × 1.94384449244`, in knots. This is surface-model wind speed, not the 500 mb wind and not gust speed. Speed is independent of grid-vector rotation.
- Instantaneous liquid-equivalent precipitation rate: PRATE × 3600, converted from mm/hour to inches/hour for the chart and CSV. It can include rain or frozen precipitation. It is **not** accumulated rain/snow depth, a probability, or an interval total. Bars denote rate samples; the space between samples is not a reconstructed accumulation.

All series use the nearest native model grid point to the airport coordinates. They are numerical guidance, not station observations, a TAF, or an official aviation forecast. Airport and nearby city/map readouts can differ because they select different grid points. Missing values remain missing, and a chart is refused when its initialization differs from the map's selected run. Official aviation forecasts: [Aviation Weather Center TAFs](https://aviationweather.gov/data/taf/).

Airport names, identifiers, types, and locations come from the [OurAirports public-domain catalog](https://ourairports.com/data/), fetched at most daily and attributed in the chart. The catalog is searched locally in the visitor's browser. Search text is not sent to a third-party geocoder. Forecast fields come from NOAA/NCEP NOMADS; temperature and precipitation reuse the validated model subsets, and a separate filtered request downloads only 10 m U/V wind. All GRIB run, lead, valid time, units, and grid definitions are checked.

## Generation and deployment

Existing dependencies in `requirements-sunset.txt` suffice. On Ubuntu with Python 3.12:

```sh
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends libeccodes0
python -m pip install -r requirements-sunset.txt
python -m models
```

The final command generates maps and airport guidance unattended. The existing daily GitHub Actions job already runs it; no extra job or repository secrets are needed. **Required environment variables: none.** To regenerate airports alone after a successful map generation, run:

```sh
python -m models.airports
```

This requires `generated/models/latest.json` and its cached `*-fields-v2.grib2` inputs from the preceding model run. Missing inputs or download/processing failures exit nonzero; the previously published airport dataset is preserved. In GitHub Actions a failure prevents a new Pages deployment. Public downloads are bounded, retried, cached under `.cache/models/`, and processed sequentially with pauses. No login, browser, desktop windows, or interactive prompt is used.

Output under `generated/models/airports/`:

```text
latest.json
catalog.json
gfs-YYYYMMDDHH-airports-NNNN.bin
hrrr-YYYYMMDDHH-airports-NNNN.bin
```

`latest.json` records generation UTC, catalog count/source/retrieval time/hash, per-model initialization, actual hours/valid times, units/field order, provenance, and bucket names/counts/hashes. Each bucket contains up to 128 airports in catalog order. Binary layout is airport × forecast time × 3 fields, little-endian Float32: temperature °F, 10 m wind knots, precipitation mm/hour. Nonfinite values mean unavailable. At 129 times a GFS bucket is at most 198,144 bytes; a visitor downloads only the selected airport's bucket, rather than all airport forecasts. The browser verifies SHA-256 and byte length. The manifest is written after its catalog and all buckets.

Upload the updated GitHub source ZIP with folders intact, including the new Python and asset files. Keep your CNAME. The existing workflow generates the model and airport assets and deploys both together. `scripts/package_site.py` includes only the airport catalog, manifest, and buckets referenced by that manifest. The larger generated assets are excluded from the GitHub source ZIP and included in the ready-to-host website ZIP.
