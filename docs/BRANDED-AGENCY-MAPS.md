# CH Weather maps of official agency forecasts

The WPC/CPC and tropical pages now default to CH Weather cartography: charcoal
canvas, original logo, green/gold header, dark geographic borders, clear legends,
and official source/validity labels. They are drawn from forecast GIS data,
not recolored or cropped agency screenshots. **The forecast remains the agency's
forecast.** No probability, forecast area, or warning is invented or upgraded.

## Products

- WPC excessive-rainfall outlooks, Days 1–3.
- WPC precipitation totals: Day 1, Days 1–3, Days 1–5, Days 1–7.
- CPC temperature and precipitation: Days 6–10, Days 8–14, Weeks 3–4, updated
  monthly outlook, and the first three-month seasonal outlook.
- NHC/CPHC 2-day and 7-day formation outlooks for the Atlantic, eastern Pacific,
  and central Pacific.

There are 17 WPC/CPC maps and six tropical maps. WPC/CPC custom maps explicitly
show **CONUS**; their official source view still provides the agency's full
geographic presentation, including Alaska/Hawaii where applicable. Tropical
basin boundaries and labels are geographic context; development areas are not
storm tracks or forecasts of landfall.

## Official data, dates and validation

WPC polygons come from NOAA's `wpc_precip_hazards` and `wpc_qpf` ArcGIS feature
services, queried as complete GeoJSON in geographic coordinates. Response errors
and truncation fail validation. Category names, accumulation units (inches),
issuance, start/end times and source URLs are retained. Small transient service
errors have three bounded attempts. The precipitation layer selection uses
the cumulative 72/120/168-hour products rather than summing overlapping maps.

An empty excessive-rainfall layer is **not automatically treated as no risk**.
The corresponding official `94/98/99epoints.txt` bulletin must explicitly state
that rainfall is not expected to exceed flash-flood guidance, have a valid date
and an unexpired window. That statement and its dates are printed on the map.
An empty QPF layer or an unsupported empty ERO layer fails the product refresh.

CPC shapefiles come from `ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/`:
`610*_latest.zip`, `814*_latest.zip`, `wk34*_latest.zip`,
`monthupd_*_latest.zip`, plus the smaller official `seaskmls_latest.zip`
for seasonal outlooks. Only `lead1_temp.kml` and `lead1_prcp.kml` are selected
from that multi-season bundle, avoiding two 48 MB shapefile downloads.
Seasonal KML polygon holes, dates, probabilities and categories are parsed from
the official geometry/attribute fields; embedded description scripts are never executed. The monthly map uses the updated monthly dataset;
an original agency image may represent a different scheduled issue, so compare
the dates rather than assuming two views are issuance-identical.

`Fcst_Date` is kept as an **issue date**, without fabricating an issue hour.
Start/end dates or `Valid_Seas` define the valid calendar interval, with calendar
month lengths and cross-year seasons handled explicitly. Probabilities and
Above/Below/Normal/EC categories are validated and retained. Probability contours
are category probabilities, not anomaly magnitude or the probability of rain.
Published near-normal regions are not silently relabeled equal chances.
Colors are stepped by the supplied contour value; the source geometry is not
re-interpolated into an invented higher-resolution forecast.

ZIP archives have download/unpacked size and file-count limits. Only expected
shapefile components are read into a temporary directory using sanitized
basenames. Readers are closed. CRS information is required and transformed to
EPSG:4326 when needed. Invalid polygon topology is repaired with Shapely's
`make_valid`, preserving valid areal pieces rather than smoothing the forecast;
CPC repair counts are recorded in metadata. Unusable geometries fail validation.

NHC/CPHC data use `gtwo_shapefiles.zip` and `gtwo_cphc_shapefiles.zip`.
Area polygons, disturbance points, basin identifiers, area numbers, and official
2-/7-day probabilities are read directly. The embedded GIS timestamp must be
recent and within 45 minutes of the basin bulletin's RSS publication time.
Missing/invalid feeds never become a quiet outlook. Zero-percent areas are
omitted for the selected period; a missing-basin layer needs an affirmative
quiet-weather bulletin. Positive points without corresponding polygons fail.

RSS **publication time** is labeled as publication, not silently substituted for
the nominal issuance time in the bulletin. The original bulletin text remains
available on the page. NHC/CPHC formation windows retain their official 2-/7-day
meaning; the GIS creation timestamp is not used as a new forecast start time.

## Website behavior

The default **CH Weather map** view loads generated local graphics. The optional
**Original agency graphic** view remains for comparison and intervening updates.
Original images are identified separately, and retrieval time never becomes a
new forecast issuance. The custom maps clearly say they are a CH Weather
presentation of official guidance, not independent agency-approved CH Weather
forecasts. The original dated tropical bulletin and current-system list remain.
These formation maps do not add hurricane tracks or invented cyclone positions.

## Commands and GitHub

Existing dependencies suffice; Cartopy includes Shapely and PyProj. No new secret
or environment variable is required. Headless rendering uses Matplotlib Agg.

```sh
python -m centers
python -m tropical
python scripts/package_site.py --check --product centers
python scripts/package_site.py --check --product tropical
```

The existing **Daily weather and sunset outlooks** workflow already has separate
`centers` and `tropical` jobs. Upload the update preserving its paths and run
that workflow. No workflow file replacement is needed. Successful artifacts are
published by **Publish latest weather website**. Generation failures exit
nonzero and preserve the previous complete local publication; other forecast
families can still publish independently. No fake replacement maps are used.

## Exact source files

Added: `centers/gis.py`, `centers/render.py`, `tropical/cartography.py`,
`tests/test_branded_guidance.py`, this guide.

Replaced: `centers/__main__.py`, `tropical/__main__.py`, `assets/centers.js`,
`assets/tropical.js`, `outlooks/centers.html`, `tropical/index.html`,
`tests/test_centers.py`, `docs/CENTERS.md`, `docs/TROPICAL.md`,
`scripts/package_github.py`.

## Source references

- [WPC GIS products](https://www.wpc.ncep.noaa.gov/html/about_gis.shtml)
- [WPC excessive-rainfall meaning](https://www.wpc.ncep.noaa.gov/qpf/excess_rain.shtml)
- [NOAA WPC QPF feature service](https://mapservices.weather.noaa.gov/vector/rest/services/precip/wpc_qpf/MapServer)
- [NOAA WPC precipitation hazards](https://mapservices.weather.noaa.gov/vector/rest/services/hazards/wpc_precip_hazards/MapServer)
- [CPC GIS archive](https://ftp.cpc.ncep.noaa.gov/GIS/us_tempprcpfcst/)
- [NHC GIS data](https://www.nhc.noaa.gov/gis/)
