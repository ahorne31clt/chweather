"""Native 3-km HRRR sunset inputs; extended cycles only, no GFS fallback."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging
import time

import cartopy.crs as ccrs
import numpy as np
import requests
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter
from shapely import intersects_xy

from .data import download
from .model import solar_sunset, destination, quality_score

LOG = logging.getLogger(__name__)
FILTER = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl'
PARAMETERS = {'lcc': ('low', 'lowCloudLayer', '%'),
              'mcc': ('middle', 'middleCloudLayer', '%'),
              'hcc': ('high', 'highCloudLayer', '%'),
              'vis': ('visibility', 'surface', 'm')}
GRID_KEYS = ('Ni', 'Nj', 'DxInMetres', 'DyInMetres', 'LaDInDegrees',
             'LoVInDegrees', 'Latin1InDegrees', 'Latin2InDegrees',
             'latitudeOfFirstGridPointInDegrees', 'longitudeOfFirstGridPointInDegrees',
             'jScansPositively', 'iScansNegatively', 'radius')


def candidate_runs(now):
    ready = now - timedelta(hours=3)
    first = ready.replace(hour=ready.hour//6*6, minute=0, second=0, microsecond=0)
    return [first-timedelta(hours=6*i) for i in range(3)]


def required_leads(run, day, min_hour, max_hour):
    offset = (datetime.combine(day, datetime.min.time(), timezone.utc)-run).total_seconds()/3600
    start, end = int(np.floor(offset+min_hour-.02)), int(np.ceil(offset+max_hour+.02))
    if run.hour not in (0, 6, 12, 18) or start < 0 or end > 48 or end-start > 12:
        raise ValueError('Extended HRRR cycle must bracket all sunsets within its 48-hour horizon')
    return list(range(start, end+1)), offset


def params_for(run, lead):
    return dict(dir=f'/hrrr.{run:%Y%m%d}/conus', file=f'hrrr.t{run:%H}z.wrfsfcf{lead:02d}.grib2',
                var_LCDC='on', var_MCDC='on', var_HCDC='on', var_VIS='on',
                lev_low_cloud_layer='on', lev_middle_cloud_layer='on',
                lev_high_cloud_layer='on', lev_surface='on')


def read_grib(path, run, lead):
    import eccodes as ec
    fields, grid = {}, None
    with Path(path).open('rb') as handle:
        while (message := ec.codes_grib_new_from_file(handle)) is not None:
            try:
                key = ec.codes_get(message, 'shortName')
                if key not in PARAMETERS or ec.codes_get(message, 'stepType') != 'instant':
                    continue
                name, level, units = PARAMETERS[key]
                if (ec.codes_get(message, 'dataDate') != int(run.strftime('%Y%m%d')) or
                    ec.codes_get(message, 'dataTime') != run.hour*100 or
                    ec.codes_get(message, 'endStep') != lead or
                    ec.codes_get(message, 'stepUnits') != 1 or
                    ec.codes_get(message, 'typeOfLevel') != level or
                    ec.codes_get(message, 'units') != units):
                    raise ValueError('HRRR field run, lead, level or units mismatch')
                current = {k: ec.codes_get(message, k) for k in GRID_KEYS}
                if (ec.codes_get(message, 'gridType') != 'lambert' or
                    current['DxInMetres'] != 3000 or current['DyInMetres'] != 3000 or
                    current['iScansNegatively'] or not current['jScansPositively'] or
                    current['Ni'] < 1700 or current['Nj'] < 1000):
                    raise ValueError('Unexpected native HRRR grid')
                if grid is not None and grid != current:
                    raise ValueError('HRRR field grids differ')
                grid = current
                values = ec.codes_get_values(message).reshape(grid['Nj'], grid['Ni'])
                if ec.codes_get(message, 'numberOfMissing') or not np.isfinite(values).all():
                    raise ValueError('Missing HRRR inputs')
                if values.min() < 0 or values.max() > (100.01 if units == '%' else 1_000_000):
                    raise ValueError('HRRR field outside plausible bounds')
                if name in fields:
                    raise ValueError('Duplicate HRRR field')
                fields[name] = (values/100 if units == '%' else values).astype('float32')
            finally:
                ec.codes_release(message)
    if set(fields) != {v[0] for v in PARAMETERS.values()}:
        raise ValueError('Missing required HRRR cloud/visibility fields')
    return grid, fields


def fetch_forecast(http, cache, day, now, min_hour, max_hour, requested_run=None):
    failures = []
    for run in ([requested_run] if requested_run else candidate_runs(now)):
        try:
            if run > now or now-run > timedelta(hours=24):
                raise ValueError('Run must be recent and not future')
            leads, offset = required_leads(run, day, min_hour, max_hour)
            cubes, urls, grid = {}, {}, None
            # Check the farthest required hour first; incomplete cycles never publish.
            for lead in [leads[-1], *leads[:-1]]:
                path = Path(cache)/f'hrrr-{run:%Y%m%d%H}-f{lead:03d}-clouds.grib2'
                query = params_for(run, lead)
                if path.exists():
                    url = requests.Request('GET', FILTER, params=query).prepare().url
                else:
                    LOG.info('Downloading HRRR %s f%03d', run.isoformat(), lead)
                    url = download(http, FILTER, path, query, maximum=20_000_000)
                    time.sleep(1)
                current, fields = read_grib(path, run, lead)
                if grid is not None and grid != current:
                    raise ValueError('HRRR hourly grids differ')
                grid = current
                cubes[lead], urls[lead] = fields, url
            return run, grid, np.array(leads)-offset, {
                key: np.stack([cubes[h][key] for h in leads]) for key in cubes[leads[0]]
            }, [urls[h] for h in leads]
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            LOG.warning('HRRR cycle %s unavailable: %s', run.isoformat(), exc)
            failures.append(str(exc))
    raise RuntimeError('No complete extended HRRR cycle covers all sunsets: '+'; '.join(failures))


def native_grid(grid):
    globe = ccrs.Globe(ellipse=None, semimajor_axis=grid['radius'], semiminor_axis=grid['radius'])
    projection = ccrs.LambertConformal(central_longitude=grid['LoVInDegrees'],
        central_latitude=grid['LaDInDegrees'],
        standard_parallels=(grid['Latin1InDegrees'], grid['Latin2InDegrees']), globe=globe)
    first = projection.transform_point(grid['longitudeOfFirstGridPointInDegrees'],
        grid['latitudeOfFirstGridPointInDegrees'], ccrs.PlateCarree())
    x = first[0]+np.arange(grid['Ni'])*grid['DxInMetres']
    y = first[1]+np.arange(grid['Nj'])*grid['DyInMetres']
    xx, yy = np.meshgrid(x, y)
    geo = ccrs.PlateCarree().transform_points(projection, xx, yy)
    return projection, x, y, geo[..., 1], geo[..., 0]


def calculate(day, grid, valid_hours, fields, usa):
    projection, x, y, lat, lon = native_grid(grid)
    mask = intersects_xy(usa, lon, lat)
    hours, azimuth = solar_sunset(day, lat, lon)
    if mask.sum() < 500_000 or hours[mask].min() < valid_hours[0] or hours[mask].max() > valid_hours[-1]:
        raise ValueError('HRRR inputs do not bracket all CONUS land sunsets')
    interpolators = {k: RegularGridInterpolator((valid_hours, y, x), v,
                     bounds_error=False, fill_value=np.nan) for k, v in fields.items()}
    raw = np.full(lat.shape, np.nan)
    indices = np.flatnonzero(mask)
    # Bound interpolation working memory on a standard GitHub runner.
    for begin in range(0, len(indices), 40_000):
        ids = indices[begin:begin+40_000]
        rows, cols = np.unravel_index(ids, lat.shape)
        t, a, b = hours.flat[ids], lat.flat[ids], lon.flat[ids]
        points = np.column_stack((t, y[rows], x[cols]))
        sampled = {k: fun(points) for k, fun in interpolators.items()}
        blockers = []
        for distance in (80, 160, 240):
            hlat, hlon = destination(a, b, azimuth.flat[ids], distance)
            projected = projection.transform_points(ccrs.PlateCarree(), hlon, hlat)
            ray = np.column_stack((t, projected[:, 1], projected[:, 0]))
            blockers.append(np.maximum(interpolators['low'](ray), .6*interpolators['middle'](ray)))
        raw.flat[ids] = quality_score(sampled['low'], sampled['middle'], sampled['high'],
                                     np.mean(blockers, axis=0), sampled['visibility'])
    covered = mask & np.isfinite(raw)
    coverage = float(covered.sum()/mask.sum())
    if coverage < .99:
        raise ValueError(f'Insufficient HRRR sunward-ray coverage: {coverage:.3%}')
    score = gaussian_filter(np.nan_to_num(raw), .65)/np.maximum(gaussian_filter(covered.astype(float), .65), 1e-12)
    score[~covered] = np.nan
    return lat, lon, score, hours, covered, coverage, projection, x, y
