# Severe/winter parameters, WOOF diagnosed type, RRFS and ECMWF IFS

This update includes maps only for RRFS and ECMWF; airport rate meteograms remain GFS/HRRR. No palette import or user-profile feature was implemented.

## Models

RRFS: NOAA operational 3 km CONUS files in noaa-rrfs-ops-pds, separate 2dfld and prslev inventories. Use 00/06/12/18 UTC, F000-F084 every 3 hours. Selected GRIB messages are fetched through HTTP Range, not whole multi-hundred-MB pressure-level files. Native categorical precipitation type/rate, surface CAPE/CIN and reflectivity are retained. MSLP uses MSLET. WMO parameter 0/16/5 is explicitly recognized as composite reflectivity where an older ecCodes table calls it unknown; encoded values are not changed.

ECMWF IFS / Euro: public 0.25-degree Open Data, main 00/12 UTC runs. F000-F144 every 3 hours, F150-F360 every 6 hours. Inventory-selected .index offsets and bounded HTTP Range downloads. Global fields are cropped to the CONUS neighborhood before rendering. Relative 500 hPa vorticity becomes absolute vorticity by adding 2*Omega*sin(latitude). Most-unstable CAPE is labeled separately; unavailable SBCAPE, CIN and gust products stay disabled. Native ptype codes map rain/thunderstorm/drizzle to rain, snow/wet snow to snow, freezing rain/drizzle to freezing liquid, ice pellets to sleet, rain-snow mix to mixed; other categories remain unclassified. MSLP uses MSL. Source credit: ECMWF Open Data / CC BY 4.0.

WOOF-NAM remains Recast's separate 12.19 km pilot (announced November 5-12, 2026), not NOAA NAM. New native downloads include CIN, gusts, reflectivity, surface pressure, 850 hPa wind and 25-hPa temperature/height profiles from 1000 through 500 hPa. Below-ground levels are excluded using surface pressure. No categorical flags or snow amounts are invented.

## Added parameters

- Approximate 2m wet-bulb temperature, Fahrenheit: Stull (2011) approximation, -20 to 50 C and 5-99% RH. Outside that input range values are missing; at saturation wet bulb equals air temperature exactly.
- Approximate surface-parcel LCL in meters AGL: max(0,125*(T-Td)), with T-Td in C. Not an observed cloud ceiling or a tornado probability.
- 10m-to-500 hPa vector shear in knots: magnitude of the wind-vector difference. This is not fixed-depth 0-6 km shear.
- Surface-based CIN magnitude in J/kg (GFS, HRRR, WOOF-NAM and RRFS).
- Native surface wind gust in knots (same four models).
- 850 hPa temperature in C and wind speed in knots (all five models).
- Simulated composite reflectivity in dBZ (HRRR, WOOF-NAM and RRFS).
- Most-unstable CAPE (ECMWF only), distinct from surface-based CAPE.

Model-grid wind components must share their vector reference before shear is computed. New scalar maps also have numerical pointer readouts and display-only smoothing.

## Experimental WOOF profile p-type + pressure

This is a deliberately conservative, uncalibrated CH Weather diagnostic. A simulated composite reflectivity threshold of 5 dBZ masks the field to modeled precipitation echoes; it is not a precipitation probability or accumulation. Surface and above-ground temperature/height profiles determine broad phase candidates. At least ten valid pressure levels are required. Cold columns at or below -0.5 C indicate snow; surface air at or above 3 C indicates rain. A >=2 C warm layer spanning at least 500 m permits melted-particle candidates: surface temperature <=-0.5 C plus a sub-500 m cold layer indicates freezing-rain potential; a cold layer deeper than 1200 m and <=-4 C permits a sleet candidate. Intermediate profiles remain uncertain. Thickness is plotted for context and never determines the type.

This dry-bulb heuristic does not resolve ice nucleation, evaporation, particle-size distributions, precipitation intensity effects, or all shallow warm/cold layers. It is not Bourgouin, Ramer, a validated precipitation-type probability model, or native WOOF output. No icing/snowfall accumulation is calculated from it.

## Rendering and storage

New exports use 1600x900 maps and lossless WebP where smaller. Native input arrays remain intact for calculations. Numeric display probes use an eight-virtual-pixel sampling lattice in the viewer's 2400x1350 coordinate system, with explicit precision metadata. Existing 2400x1350 PNG/WebP frames remain compatible. Smoothing scales annotation layers to the virtual coordinate system and never modifies underlying values. The site keeps the bounded image cache introduced previously. If the complete exported site exceeds 900 MB, the publication-only budget helper reduces model display graphics in bounded steps (1280, 1120, then 960 pixels wide), updates every affected image hash, and preserves numeric grids and all forecast hours. If it still cannot fit, it refuses the deployment rather than exceeding the GitHub Pages limit. Source artifacts remain unchanged. The publishing job installs the same pinned Pillow version already used by generators and allows up to 60 minutes for collection/compaction; no credentials are added.

## Install and run

No new credentials, environment variables, or dependencies beyond existing requirements-sunset.txt and ecCodes.

    python -m models --model rrfs --workers 2
    python -m models --model ecmwf --workers 2
    python -m models --model woofnam --workers 2

Upload source files at the same repository paths, then run Scheduled weather models. Its independent matrix is gfs, hrrr, woofnam, rrfs, ecmwf; fail-fast remains false. Publish latest weather website follows and can retain prior successful models if another model fails. New selections become usable when their generated artifacts are published; uploading HTML alone does not generate runs.

Validation: real F024 fields/maps for the three added models; RRFS F000/F084 and ECMWF F000/F360 field decoding; GFS/HRRR added-field retrieval and map rendering; synthetic phase/shear/unit tests; browser controls/readouts/smoothing checks. Full new forecast cycles must be generated by the workflow before publication. This update does not claim observed forecast skill for the experimental type diagnosis.

## Primary references

https://registry.opendata.aws/noaa-rrfs-ops/
https://www.ecmwf.int/en/forecasts/datasets/open-data
https://codes.ecmwf.int/grib/format/grib2/ctables/4/201/
https://woof-nam.recastsystems.com/README.txt
https://www.weather.gov/ama/preciptypes
https://journals.ametsoc.org/view/journals/apme/50/11/jamc-d-11-0143.1.xml
