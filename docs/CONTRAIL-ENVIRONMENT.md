# Persistent contrail environment

In `/optics/`, select **Persistent contrail environment**. It has national and
North Carolina maps, hourly city categories, and a selected-layer readout of
pressure, temperature and ice-relative humidity. It is conditional on a suitable
aircraft crossing the layer. No flight traffic or airport-distance boost is used.

## Interpretation

- **No qualifying sampled layer:** none of the tested pressure surfaces met the
  assumed exhaust-mixing formation criterion. This does not exclude a thin
  suitable layer between surfaces.
- **Formation only:** the formation test is met, but ambient air is below ice
  saturation, so the persistence condition is not met.
- **Persistence environment:** formation test met and ice-relative humidity at
  least 100%. A contrail could persist and spread, but its survival and lifetime
  are not modeled.

The map is the highest category at any sampled level/hour over the displayed
window. It is not a simultaneous map of cloud presence, a 0–100 score, a forecast
probability, or a measurement of ice supersaturation. Nighttime formation is
allowed. Low high-cloud cover does not suppress this view. Natural cirrus need
not already exist. Existing halo, sundog and arc scores remain separate; their
required crystal shapes/orientations are not established by contrail formation.

## Reproducible physics

GFS temperature and **specific humidity** are requested at 200, 250, 300 and
350 hPa, retaining the original ice-optics fields at 300/400/500 hPa. Native
0.25-degree and three-hour inputs are linearly interpolated hourly. Specific
humidity avoids assuming whether the provider's RH reference is ice, water or
mixed phase. It does not eliminate upper-air moisture errors.

With `q` in kg/kg, `p` in Pa, and epsilon 0.622, vapor pressure is
`e = q*p / (epsilon + (1-epsilon)*q)`. Ice-relative humidity is
`RHi = e / e_sat_ice(T)`. Saturation vapor pressures use the Murphy–Koop
formulations, in Kelvin and Pa.

The Schmidt–Appleman exhaust mixing-line slope is
`G = EI_H2O * cp * p / (epsilon * Q_fuel * (1-eta))`.
Assumptions: water emission index 1.25 kg/kg, air heat capacity 1004 J/kg/K,
fuel heat 43 MJ/kg and engine efficiency 0.35. These are generic research inputs,
not measurements for any flight or a claim that all aircraft behave alike.

The tangent temperature `T_LM` solves `d(e_sat_water)/dT = G`. The implemented
formation test requires `T < T_LM` and
`e + G*(T_LM-T) >= e_sat_water(T_LM)`: the exhaust-mixing line reaches liquid
saturation. The persistence category additionally requires `RHi >= 1`.
Each pressure surface is evaluated independently, then the highest category is
selected; among tied categories the moistest ice-relative level is reported.

No humidity scaling is fitted, and no artificial near-saturation bonus is added.
The coarse vertical sampling, engine assumptions, model humidity biases,
interpolation, wake-vortex losses, mixing, sedimentation, wind shear and cloud
advection can all change a real outcome. No cloud lifetime or halo occurrence is
calculated. A future observational evaluation is needed before interpreting
these categories as useful local forecasting skill.

## Sources

- [FAA contrail explanation](https://www.faa.gov/contrails)
- [pycontrails Schmidt–Appleman implementation documentation](https://py.contrails.org/api/pycontrails.models.sac.html)
- [pycontrails persistent contrail regions](https://py.contrails.org/api/pycontrails.models.pcr.html)
- [Murphy & Koop (2005)](https://doi.org/10.1256/qj.04.94)
- [UCAR saturation vapor pressure formulations](https://www.eol.ucar.edu/data-software/conventions-and-standards/water-vapor-pressure-formulations)

This project implements its own compact mixing-line calculation with existing
NumPy/SciPy dependencies. It does not run pycontrails, CoCiP, or an aircraft
trajectory/lifetime model, and is not endorsed by the cited organizations.

## Setup and exact files

No new environment variable, secret, dependency or workflow is required.
`python -m optics` downloads the additional fields and renders all 14 maps.
`python scripts/package_site.py --check --product optics` checks outputs.
New source cache names prevent reusing incomplete old GFS field subsets.

Replace: `optics/data.py`, `optics/science.py`, `optics/__main__.py`,
`optics/render.py`, `optics/index.html`, `assets/optics.js`, `assets/optics.css`,
`scripts/package_github.py`. Add: `optics/contrails.py`, `tests/test_contrails.py`,
this guide. The upload ZIP contains these exact paths. Generated PNG/JSON files
are rebuilt by Actions rather than uploaded as source.

After uploading, run **Daily weather and sunset outlooks**. Its independent
optics job generates the new maps and its successful artifact is picked up by
the existing publisher. The page shows an unavailable message for a new view
until a matching forecast has been published.
