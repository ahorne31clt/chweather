from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import re

import eccodes as ec
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import shape
from cartopy.io import shapereader

from sunset.data import download

UTC = timezone.utc
NDFD = 'https://tgftp.nws.noaa.gov/SL.us008001/ST.opnl/DF.gr2/DC.ndfd/AR.conus/VP.001-003'


def iso(value):
    return value.isoformat(timespec='seconds').replace('+00:00', 'Z')


def parse_iso(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)


def wmo_time(code, anchor):
    """Resolve DDHHMM across month/year boundaries without assuming this month."""
    day, hour, minute = int(code[:2]), int(code[2:4]), int(code[4:6])
    candidates = []
    for offset in range(-32, 33):
        candidate = anchor + timedelta(days=offset)
        if candidate.day == day:
            candidates.append(candidate.replace(hour=hour, minute=minute, second=0, microsecond=0))
    if not candidates:
        raise ValueError('Invalid WMO timestamp')
    return min(candidates, key=lambda value: abs((value-anchor).total_seconds()))


SPC_CATEGORIES = {
    'TSTM': ('General thunderstorms', '#C1E9C1'),
    'MRGL': ('Marginal', '#66A366'),
    'SLGT': ('Slight', '#FFE65A'),
    'ENH': ('Enhanced', '#FFA45B'),
    'MDT': ('Moderate', '#FF6060'),
    'HIGH': ('High', '#EF53ED'),
}


def validate_spc(collection, text, day, now):
    if collection.get('type') != 'FeatureCollection' or not isinstance(collection.get('features'), list):
        raise ValueError('Not an SPC FeatureCollection')
    issue_match = re.search(r'SPC AC (\d{6})', text)
    valid_match = re.search(r'Valid\s+(\d{6})Z\s*-\s*(\d{6})Z', text)
    if not issue_match or not valid_match:
        raise ValueError('SPC issuance/validity missing')
    issue = wmo_time(issue_match[1], now)
    start = wmo_time(valid_match[1], issue+timedelta(days=day-1))
    end = wmo_time(valid_match[2], start+timedelta(hours=24))
    if issue > now+timedelta(minutes=10) or now-issue > timedelta(hours=48) or end <= now or not start < end:
        raise ValueError('SPC data are expired or have invalid dates')
    records = []
    for feature in collection['features']:
        prop = feature['properties']
        if prop['LABEL'] not in SPC_CATEGORIES:
            raise ValueError('Unknown SPC risk category; do not substitute a category')
        for key, expected in [('ISSUE',issue),('VALID',start),('EXPIRE',end)]:
            actual = datetime.strptime(prop[key], '%Y%m%d%H%M').replace(tzinfo=UTC)
            if actual != expected:
                raise ValueError('SPC polygons and discussion are from different issuances')
        geometry = shape(feature['geometry'])
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError('Invalid SPC geometry')
        records.append((prop['LABEL'], geometry))
    summary_match = re.search(r'\.\.\.SUMMARY\.\.\.\s*(.*?)(?:\n\s*\n|\n\.\.\.)', text, re.S)
    summary = ' '.join(summary_match[1].split()) if summary_match else 'See the official SPC discussion for the complete outlook.'
    return records, dict(issued_at_utc=iso(issue),valid_start_utc=iso(start),valid_end_utc=iso(end),summary=summary)


def get_spc(http, cache, day, now):
    base = f'https://www.spc.noaa.gov/products/outlook/day{day}otlk'
    # A product can update between the two requests; retry the pair once.
    for attempt in range(2):
        path = cache/f'spc-day{day}.geojson'
        download(http, base+'_cat.nolyr.geojson', path, maximum=2_000_000)
        text_path = cache/f'spc-day{day}.txt'
        download(http, base+'.txt', text_path, maximum=1_000_000)
        try:
            records, meta = validate_spc(json.loads(path.read_text()),text_path.read_text(),day,now)
            return records,dict(meta,source_urls=[base+'_cat.nolyr.geojson',base+'.txt'],
                                source='NOAA/NWS Storm Prediction Center',kind='Official SPC categorical outlook; CH Weather presentation')
        except ValueError:
            if attempt: raise


def ndfd_period(message):
    end = datetime(*(ec.codes_get(message,key) for key in (
        'yearOfEndOfOverallTimeInterval','monthOfEndOfOverallTimeInterval',
        'dayOfEndOfOverallTimeInterval','hourOfEndOfOverallTimeInterval',
        'minuteOfEndOfOverallTimeInterval')),tzinfo=UTC)
    unit = ec.codes_get(message,'indicatorOfUnitForTimeRange')
    length = ec.codes_get(message,'lengthOfTimeRange')
    unit_seconds = {0:60,1:3600,2:86400}.get(unit)
    if unit_seconds is None: raise ValueError('Unsupported NDFD period unit')
    return end-timedelta(seconds=length*unit_seconds), end


def get_ndfd(http, cache, element, now):
    """Decode an actual forecast period, preserving missing-data masks."""
    path = cache/f'{element}.bin'
    url = f'{NDFD}/ds.{element}.bin'
    download(http,url,path,maximum=20_000_000)
    with path.open('rb') as handle:
        while (gid := ec.codes_grib_new_from_file(handle)) is not None:
            try:
                if (ec.codes_get(gid,'discipline'),ec.codes_get(gid,'parameterCategory'),ec.codes_get(gid,'parameterNumber')) != (
                    (0,1,8) if element=='pop12' else (0,0,4)):
                    raise ValueError('Unexpected NDFD weather element')
                start,end = ndfd_period(gid)
                if end <= now: continue
                # Use the daytime 12–00 UTC interval, never call a max/union of
                # two PoPs a 24-hour probability. Same period as the high temp.
                if end.hour != 0: continue
                issue = datetime.strptime(str(ec.codes_get(gid,'dataDate'))+f"{ec.codes_get(gid,'dataTime'):04d}",'%Y%m%d%H%M').replace(tzinfo=UTC)
                validate_ndfd_reference(issue,now)
                if (end-start).total_seconds()!=43200:
                    raise ValueError('Expected a 12-hour NDFD interval')
                if element=='pop12':
                    threshold=ec.codes_get(gid,'scaledValueOfUpperLimit')*10.0**(-ec.codes_get(gid,'scaleFactorOfUpperLimit'))
                    if ec.codes_get(gid,'probabilityType')!=1 or not np.isclose(threshold,.254):
                        raise ValueError('Unexpected precipitation probability threshold')
                rows,cols = ec.codes_get(gid,'Ny'),ec.codes_get(gid,'Nx')
                values = ec.codes_get_values(gid).reshape(rows,cols)[::2,::2]
                lat = ec.codes_get_array(gid,'latitudes').reshape(rows,cols)[::2,::2]
                lon = (ec.codes_get_array(gid,'longitudes').reshape(rows,cols)[::2,::2]+180)%360-180
                missing=ec.codes_get(gid,'missingValue')
                good=np.isfinite(values)&(values!=missing)&(values<9000)
                if good.sum()<10000: raise ValueError('NDFD coverage is unexpectedly sparse')
                if element=='pop12':
                    if values[good].min()<0 or values[good].max()>100: raise ValueError('Invalid PoP percentages')
                else:
                    if values[good].min()<180 or values[good].max()>350: raise ValueError('Invalid temperatures')
                    values=(values-273.15)*9/5+32
                points=np.column_stack([lon[good],lat[good]])
                return cKDTree(points),values[good],dict(source='NOAA/NWS National Digital Forecast Database',
                    source_urls=[url],issued_at_utc=iso(issue),valid_start_utc=iso(start),valid_end_utc=iso(end),
                    reference_time_utc=iso(issue),timestamp_kind='NDFD production reference',
                    kind='Official NWS forecast grids; CH Weather presentation',
                    native_grid_km=2.5,render_sampling='Every second native grid point; nearest-neighbor sampling',
                    units='percent' if element=='pop12' else 'degrees Fahrenheit')
            finally: ec.codes_release(gid)
    raise ValueError(f'No unexpired daytime {element} forecast interval')


def validate_ndfd_reference(reference,now):
    """NDFD headers identify a nominal production cycle, not file publication.

    A downloaded 18:17 UTC file can already carry the 18:30 UTC cycle.
    Permit one 30-minute production slot; retain the 24-hour age limit.
    """
    if reference>now+timedelta(minutes=30) or now-reference>timedelta(hours=24):
        raise ValueError(f'NDFD production reference outside allowed window: reference={iso(reference)}, checked={iso(now)} (maximum age 24h, lead 30m)')


def sample_ndfd(tree, values, latitudes, longitudes):
    lon,lat=np.meshgrid(longitudes,latitudes)
    distance,index=tree.query(np.column_stack([lon.ravel(),lat.ravel()]),distance_upper_bound=.1)
    result=np.full(index.shape,np.nan)
    good=np.isfinite(distance)
    result[good]=values[index[good]]
    return result.reshape(lat.shape)


def get_nc(http, cache):
    name='ne_50m_admin_1_states_provinces'
    folder=cache/name
    path=folder/(name+'.shp')
    if not path.exists():
        import zipfile
        archive=cache/(name+'.zip')
        download(http,f'https://naturalearth.s3.amazonaws.com/50m_cultural/{name}.zip',archive)
        with zipfile.ZipFile(archive) as zipped:
            for member in zipped.infolist():
                if '/' in member.filename or '\\' in member.filename or member.file_size>30_000_000:
                    raise ValueError('Unexpected geography archive member')
            zipped.extractall(folder)
    return next(r.geometry for r in shapereader.Reader(path).records()
                if r.attributes.get('name')=='North Carolina' and r.attributes.get('admin')=='United States of America')


def get_foliage(http, cache, day):
    """Use the same public dated raster as the earlier Remotion project.

    This deliberately does not bypass the location API's 403 response.
    """
    from PIL import Image
    import requests
    if day.month not in (9,10,11,12):
        return None,dict(status='out_of_season',source='Explore Fall',source_urls=['https://www.explorefall.com/fall-foliage-map'])
    for back in range(3):
        source_day=day-timedelta(days=back)
        url=f'https://www.explorefall.com/maps/{source_day.year}-highres/{source_day:%Y%m%d}.png'
        path=cache/'foliage.png'
        try: download(http,url,path,maximum=8_000_000)
        except requests.HTTPError as exc:
            if exc.response.status_code in (403,404): continue
            raise
        with Image.open(path) as image:
            image.verify()
        return path,dict(source='Explore Fall',source_urls=[url,'https://www.explorefall.com/fall-foliage-map'],
            source_date=source_day.isoformat(),forecast_valid_date=source_day.isoformat(),
            kind='Explore Fall published daily foliage-model estimate, not a direct observation',
            valid_start_utc=f'{source_day.isoformat()}T00:00:00Z',
            valid_end_utc=f'{(source_day+timedelta(days=1)).isoformat()}T00:00:00Z',
            georeferencing='Publisher Web Mercator image bounds: west -126, east -65, south 23, north 52',
            location_api_status='API access returned HTTP 403; no peak-date API forecast is claimed')
    raise ValueError('No recent published Explore Fall foliage map is available')
