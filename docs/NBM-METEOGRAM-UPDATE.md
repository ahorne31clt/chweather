# NBM and model comparisons

Replace these five files at the same paths in GitHub: mos/index.html, assets/mos.js, models/index.html, assets/meteogram.js, assets/models.css.

NBH, NBS and NBE are original NWS National Blend of Models text bulletins delivered by Iowa Environmental Mesonet. Station, family, initialization and required forecast rows are checked. Older bulletins are explicitly marked. No login or environment variables are required. Documentation: https://vlab.noaa.gov/web/mdl/nbm-text-products

Open Models > Airport meteogram, choose an airport and enable Overlay the other available model. The primary selection controls the time span and View this hour on map. Lines use actual valid UTC timestamps and their own initialization times. Missing exact-time samples are labeled; forecasts are not extended beyond their horizon. CSV includes both selected models and all their available times. PNG includes both curves and initialization labels. This comparison is not a calibrated ensemble probability forecast.

After upload run Publish latest weather website. No model regeneration is required for this interface update; overlays use published airport data. Regular Scheduled weather models runs continue refreshing it.
