# Persistent contrail environment

In `/optics/`, select **Persistent contrail environment**. It has national and
North Carolina maps, hourly city categories, and a selected-layer readout of
pressure, temperature and ice-relative humidity. It is conditional on a suitable
aircraft crossing the layer. No flight traffic or airport-distance boost is used.

## Interpretation

- **No qualifying sampled layer:** none of the tested pressure surfaces met the
  assumed exhaust-mixing formation criterion. This does not exclude a thin
  suitable layer between surfaces.
- **Formation only:** the formation test is met and modeled humidity is below
  90% relative to ice.
- **Near ice saturation:** formation is possible and modeled ice-relative humidity
  is 90% to below 100%. This is an experimental uncertainty category.
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

GFS temperature and specific humidity are sampled at 150, 200, 250, 300,
350 and 400 hPa. When a complete extended HRRR pressure subset is available,
HRRR adds nine independent pressure levels from 200 to 400 hPa at 25 hPa
spacing. Each HRRR profile is sampled at the nearest native point to the 0.25°
display grid. Both sources are interpolated hourly from three-hourly inputs.
The highest category supported by either model is displayed. HRRR is selected
on a tie where available, and the location view reports both categories.

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

The near-saturation category leaves the original humidity values and 100% persistence threshold intact.
The coarse vertical sampling, engine assumptions, model humidity biases,
interpolation, wake-vortex losses, mixing, sedimentation, wind shear and cloud
advection can all change a real outcome. No cloud lifetime or halo occurrence is
calculated. A future observational evaluation is needed before interpreting
these categories as useful local forecasting skill.

## Charlotte comparison, November 6, 2026

At about noon EST, the archived 06 UTC GFS forecast interpolated to 17 UTC at
35.25°N, 80.75°W gave 91.6% ice-relative humidity at 200 hPa with the formation
criterion met. The sampled 06 UTC HRRR profile was drier. The old category
would have shown formation only. The revised category flags near saturation.
Neither sampled profile reproduced a persistence environment at that point.
This single reported observation does not establish forecast skill.

## Sources

- [How well can persistent contrails be predicted? An update](https://acp.copernicus.org/articles/24/7911/2024/)
- [FAA contrail explanation](https://www.faa.gov/contrails)
- [pycontrails Schmidt–Appleman implementation documentation](https://py.contrails.org/api/pycontrails.models.sac.html)
- [pycontrails persistent contrail regions](https://py.contrails.org/api/pycontrails.models.pcr.html)
- [Murphy & Koop (2005)](https://doi.org/10.1256/qj.04.94)
- [UCAR saturation vapor pressure formulations](https://www.eol.ucar.edu/data-software/conventions-and-standards/water-vapor-pressure-formulations)

This project implements its own compact mixing-line calculation with existing
NumPy/SciPy dependencies. It does not run pycontrails, CoCiP, or an aircraft
trajectory/lifetime model, and is not endorsed by the cited organizations.

## Regeneration

Run `python -m optics` or the **Daily weather and sunset outlooks** workflow.
The HRRR pressure fields are optional and the forecast uses GFS when the HRRR
subset is unavailable. The website continues to interpret earlier published
three-category forecasts until the new forecast arrives.
