# Satellite viewer

Open `/satellite/`. This plain HTML/CSS/JavaScript viewer fetches the current published frame list directly from NOAA/NESDIS/STAR and displays its timestamped images unchanged. No credentials, dependencies, backend, or GitHub Actions imagery job is required. Existing Pages deployment packages the page; adding `satellite/**` to the workflow push paths triggers deployment when the page changes.

GOES-East (19) and GOES-West (18); CONUS and full disk; East Southeast/Carolinas and Northeast views. Products: GeoColor, clean infrared band 13, water vapor bands 8/9/10, red visible band 2, Air Mass RGB, day/night cloud microphysics and Sandwich composite. Regional East views switch to CONUS when West is selected.

Controls: 12/24-frame timeline, first/previous/play/next/latest, speed, UTC/Eastern time, zoom/pan/Fit, fullscreen where supported, original image and NOAA-source links. Auto refresh checks every five minutes while enabled, visible and paused. Arrow keys, Home/End and Space work outside focused controls. Selected settings are preserved in the URL.

The source is NOAA's `conus_band.php`, `fulldisk_band.php`, or `sector_band.php` page. Only explicitly published `img` frames with IDs beginning `F_` and HTTPS `cdn.star.nesdis.noaa.gov` URLs matching the selected satellite, sector and product are accepted. The remote HTML is parsed without executing scripts or inserting it into the page. Scan dates are decoded from YYYY + UTC day-of-year + HHMM in each original image filename. Missing scans are not synthesized. Delayed frames older than one hour are labeled; refresh failures clear the selected image rather than mislabel old imagery. A direct official viewer link remains available.

CONUS is commonly five-minute imagery; sectors and full disk commonly ten-minute imagery. Processing delay and data gaps can vary. GeoColor uses approximate true color by day and infrared at night; city lights are a static orientation layer. Water vapor is not surface humidity; infrared brightness temperature is not 2-m air temperature. Source imagery retains NOAA borders and legends. No numerical pixel sampling is provided. Zoom does not increase native resolution.

Only the latest and next two frames are prefetched, with at most 26 image objects retained; 20-second request timeouts. Internet access to both NOAA hosts and browser CORS support are necessary. If a host is unavailable or NOAA changes its markup, an honest unavailable state and source link are shown. Image loops refresh in the browser independently of the 8 a.m. forecast generation. Browser background tabs pause animation.

Sources: [NOAA GOES viewer](https://www.star.nesdis.noaa.gov/GOES/) and [GeoColor description/credit](https://www.star.nesdis.noaa.gov/GOES/conus_band.php?sat=G19&band=GEOCOLOR&length=12). Imagery credit: NOAA/NESDIS/STAR; GeoColor CIRA/NOAA.

## Exact files added or replaced

Added: `satellite/index.html`, `assets/satellite.css`, `assets/satellite.js`, `docs/SATELLITE.md`.

Replaced: `index.html`, `models/index.html`, `outlooks/index.html`, `sunset/index.html`, `tropical/index.html` (navigation); `scripts/package_site.py` (static export); `.github/workflows/sunset.yml` (push path); `README.md` (viewer documentation); `output/ch-weather-github-ready.zip`, `output/ch-weather-website.zip` (packages). Matching `_site/` preview copies are refreshed. No generated weather data, Python model code or dependencies are changed.

Upload the extracted GitHub-ready ZIP contents with folders preserved and keep the existing CNAME. No additional Actions step or secret is needed for satellite imagery.
