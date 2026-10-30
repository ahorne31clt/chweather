"""Bounded public NOAA downloads; only a small CONUS subset, never full GFS."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging
import time
import zipfile

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOG = logging.getLogger(__name__)
FILTER = 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl'
# Padding for the 240-km sunward ray; scoring is later cropped to lower48.
BBOX = dict(leftlon=228, rightlon=298, bottomlat=20, toplat=54)
PARAMETERS = {'lcc':'low','mcc':'middle','hcc':'high','vis':'visibility'}


def session():
    result = requests.Session()
    retry = Retry(total=2, backoff_factor=1.5, status_forcelist=[429,500,502,503,504],
                  respect_retry_after_header=False)
    result.mount('https://', HTTPAdapter(max_retries=retry))
    result.headers['User-Agent'] = 'CHWeatherSunset/1.0 (public GFS subset)'
    return result


def download(http, url, path, params=None, maximum=12_000_000):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.part')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with http.get(url, params=params, timeout=(15,90), stream=True) as response:
            response.raise_for_status()
            size = 0
            with temporary.open('wb') as handle:
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > maximum:
                        raise ValueError(f'Download exceeded {maximum} bytes')
                    handle.write(chunk)
        if size == 0:
            raise ValueError('Empty response')
        temporary.replace(path)
        return response.url
    finally:
        temporary.unlink(missing_ok=True)


def params_for(run, lead):
    return dict(dir=f'/gfs.{run:%Y%m%d}/{run:%H}/atmos',
                file=f'gfs.t{run:%H}z.pgrb2.0p25.f{lead:03d}',
                var_LCDC='on',var_MCDC='on',var_HCDC='on',var_VIS='on',
                lev_low_cloud_layer='on',lev_middle_cloud_layer='on',
                lev_high_cloud_layer='on',lev_surface='on',subregion='',**BBOX)


def read_grib(path, run, lead):
    import eccodes as ec
    try:
        return _read_grib(path, run, lead)
    except ec.CodesInternalError as exc:
        raise ValueError(f'Invalid GRIB response: {type(exc).__name__}') from exc


def _read_grib(path, run, lead):
    import eccodes as ec
    fields = {}
    latitudes = longitudes = None
    with Path(path).open('rb') as handle:
        while (message := ec.codes_grib_new_from_file(handle)) is not None:
            try:
                key = ec.codes_get(message,'shortName')
                # Filter returns time-averaged cloud records too. Accept ONLY
                # instantaneous fields; silently mixing them would bias scoring.
                if key not in PARAMETERS or ec.codes_get(message,'stepType') != 'instant':
                    continue
                expected = int(run.strftime('%Y%m%d'))
                if (ec.codes_get(message,'dataDate') != expected or
                    ec.codes_get(message,'dataTime') != run.hour*100 or
                    ec.codes_get(message,'endStep') != lead):
                    raise ValueError('GRIB run or lead differs from requested forecast')
                rows, cols = ec.codes_get(message,'Nj'), ec.codes_get(message,'Ni')
                lat = ec.codes_get_array(message,'latitudes').reshape(rows,cols)[:,0]
                lon = ec.codes_get_array(message,'longitudes').reshape(rows,cols)[0,:]
                lon = (lon+180)%360-180
                data = ec.codes_get_values(message).reshape(rows,cols)
                if ec.codes_get(message,'bitmapPresent') or not np.isfinite(data).all():
                    raise ValueError('Missing or nonfinite GFS values')
                if key in ('lcc','mcc','hcc'):
                    if data.min() < -.01 or data.max() > 100.01:
                        raise ValueError('Cloud cover outside 0-100 percent')
                    data = np.clip(data/100,0,1)
                elif data.min() < 0 or data.max() > 1_000_000:
                    raise ValueError('Visibility outside plausible bounds')
                lat_order, lon_order = np.argsort(lat), np.argsort(lon)
                data = data[np.ix_(lat_order,lon_order)]
                lat, lon = lat[lat_order], lon[lon_order]
                if latitudes is not None and (not np.array_equal(lat,latitudes) or not np.array_equal(lon,longitudes)):
                    raise ValueError('GFS fields have inconsistent grids')
                latitudes, longitudes = lat, lon
                name = PARAMETERS[key]
                if name in fields:
                    raise ValueError(f'Duplicate instantaneous {name}')
                fields[name] = data
            finally:
                ec.codes_release(message)
    if set(fields) != set(PARAMETERS.values()):
        raise ValueError(f'Missing GFS variables; found {list(fields)}')
    if len(latitudes) < 100 or len(longitudes) < 200:
        raise ValueError('Unexpectedly small GFS grid')
    return latitudes,longitudes,fields


def candidate_runs(now):
    # Four-hour publication allowance, then bounded fallback (max age 22 h).
    ready = now-timedelta(hours=4)
    first = ready.replace(hour=ready.hour//6*6,minute=0,second=0,microsecond=0)
    return [first-timedelta(hours=6*i) for i in range(3)]


def fetch_forecast(http, cache, day, now, min_hour, max_hour, requested_run=None):
    midnight = datetime(day.year,day.month,day.day,tzinfo=timezone.utc)
    failures = []
    for run in ([requested_run] if requested_run else candidate_runs(now)):
        try:
            if run > now or now-run > timedelta(hours=24):
                raise ValueError('Run must be no more than 24 hours old and not future')
            offset = (midnight-run).total_seconds()/3600
            start = int(np.floor((offset+min_hour)/3))*3
            end = int(np.ceil((offset+max_hour)/3))*3
            leads = list(range(start,end+1,3))
            if start < 3 or end > 72 or len(leads)>9:
                raise ValueError('Date outside supported short-range forecast window')
            cubes, urls = {}, []
            base_lat = base_lon = None
            for lead in leads:
                path = Path(cache)/f'gfs-{run:%Y%m%d%H}-f{lead:03d}.grib2'
                query = params_for(run,lead)
                # Always validate cached data with exactly the same parser.
                if path.exists():
                    url = requests.Request('GET',FILTER,params=query).prepare().url
                else:
                    LOG.info('Downloading GFS %s f%03d',run.isoformat(),lead)
                    url = download(http,FILTER,path,query)
                    time.sleep(1)  # sequential, polite requests to public NOMADS
                lat,lon,fields = read_grib(path,run,lead)
                if base_lat is not None and (not np.array_equal(base_lat,lat) or not np.array_equal(base_lon,lon)):
                    raise ValueError('GFS timestep grids differ')
                base_lat,base_lon = lat,lon
                for key,values in fields.items():
                    cubes.setdefault(key,[]).append(values)
                urls.append(url)
            return run,base_lat,base_lon,np.array(leads)-offset,{k:np.stack(v) for k,v in cubes.items()},urls
        except (requests.RequestException,ValueError,RuntimeError) as exc:
            LOG.warning('GFS run %s unusable: %s',run.isoformat(),exc)
            failures.append(f'{run.isoformat()}: {exc}')
    raise RuntimeError('No complete recent GFS run available: '+'; '.join(failures))


def geography(http, cache):
    from cartopy.io import shapereader
    from shapely.geometry import box
    paths = []
    for dataset in ('admin_0_countries','admin_1_states_provinces_lines'):
        folder = Path(cache)/f'ne_50m_{dataset}'
        shape = folder/f'ne_50m_{dataset}.shp'
        if not shape.exists():
            archive = Path(cache)/f'ne_50m_{dataset}.zip'
            download(http,f'https://naturalearth.s3.amazonaws.com/50m_cultural/ne_50m_{dataset}.zip',archive)
            with zipfile.ZipFile(archive) as zipped:
                for member in zipped.infolist():
                    # Fixed trusted archive; still forbid traversal/zip bombs.
                    if '/' in member.filename or '\\' in member.filename or member.file_size>30_000_000:
                        raise ValueError('Unexpected Natural Earth archive member')
                zipped.extractall(folder)
        paths.append(shape)
    countries = list(shapereader.Reader(paths[0]).records())
    usa = next(r.geometry for r in countries if r.attributes['ADMIN']=='United States of America')
    usa = usa.intersection(box(-125,24,-66,50))
    states = list(shapereader.Reader(paths[1]).geometries())
    return usa,[r.geometry for r in countries],states
