from datetime import datetime,timedelta,timezone
from pathlib import Path
import csv,gzip,io,logging

import eccodes as ec
import numpy as np
import requests
from shapely import intersects_xy
from sunset.data import download

FILTER='https://nomads.ncep.noaa.gov/cgi-bin/filter_rtma2p5.pl'
METARS='https://aviationweather.gov/data/cache/metars.cache.csv.gz'
KEYS={'2t':('temperature',2,'K',150,350),'2d':('dewpoint',2,'K',150,350),
      '10si':('wind',10,'m s**-1',0,130),'i10fg':('gust',10,'m s**-1',0,160)}


def read_grib(path,run):
    fields={};grid=None
    with Path(path).open('rb') as handle:
        while (g:=ec.codes_grib_new_from_file(handle)) is not None:
            try:
                short=ec.codes_get(g,'shortName')
                if short not in KEYS:continue
                name,level,units,low,high=KEYS[short]
                if (ec.codes_get(g,'dataDate')!=int(run.strftime('%Y%m%d')) or ec.codes_get(g,'dataTime')!=run.hour*100 or
                    ec.codes_get(g,'endStep')!=0 or ec.codes_get(g,'stepType')!='instant' or
                    ec.codes_get(g,'typeOfLevel')!='heightAboveGround' or ec.codes_get(g,'level')!=level or ec.codes_get(g,'units')!=units):
                    raise ValueError('RTMA time, level, step or units mismatch')
                current=dict(id=ec.codes_get(g,'md5GridSection'),type=ec.codes_get(g,'gridType'),
                    rows=ec.codes_get(g,'Nj'),cols=ec.codes_get(g,'Ni'),
                    first_lat=ec.codes_get(g,'latitudeOfFirstGridPointInDegrees'),first_lon=ec.codes_get(g,'longitudeOfFirstGridPointInDegrees'),
                    j_positive=ec.codes_get(g,'jScansPositively'),i_negative=ec.codes_get(g,'iScansNegatively'),earth_radius=ec.codes_get(g,'radius'))
                for out,key in [('central_lon','LoVInDegrees'),('central_lat','LaDInDegrees'),('parallel1','Latin1InDegrees'),('parallel2','Latin2InDegrees'),('dx','DxInMetres'),('dy','DyInMetres')]:current[out]=ec.codes_get(g,key)
                if current['type']!='lambert' or not 2400<current['dx']<2600 or not 2400<current['dy']<2600:
                    raise ValueError('Unexpected RTMA native grid')
                if grid and grid!=current:raise ValueError('RTMA field grids differ')
                grid=current
                values=ec.codes_get_values(g).reshape(grid['rows'],grid['cols']).astype('float32')
                if ec.codes_get(g,'numberOfMissing'):values[values==ec.codes_get(g,'missingValue')]=np.nan
                good=values[np.isfinite(values)]
                if good.size<values.size*.9 or good.min()<low or good.max()>high:raise ValueError('Invalid RTMA field values')
                if name in fields:raise ValueError('Duplicate RTMA field')
                fields[name]=values
            finally:ec.codes_release(g)
    if set(fields)!={p[0] for p in KEYS.values()}:raise ValueError('Missing RTMA surface fields')
    return fields,grid


def fetch_rtma(http,cache,now):
    first=(now-timedelta(hours=1)).replace(minute=0,second=0,microsecond=0)
    failures=[]
    for offset in range(3):
        run=first-timedelta(hours=offset)
        query=dict(dir=f'/rtma2p5.{run:%Y%m%d}',file=f'rtma2p5.t{run:%H}z.2dvaranl_ndfd.grb2_wexp',
            var_TMP='on',var_DPT='on',var_WIND='on',var_GUST='on',lev_2_m_above_ground='on',lev_10_m_above_ground='on')
        path=Path(cache)/f'rtma-{run:%Y%m%d%H}.grib2'
        try:
            url=requests.Request('GET',FILTER,params=query).prepare().url
            if not path.exists():download(http,FILTER,path,query,maximum=30_000_000)
            fields,grid=read_grib(path,run)
            return run,fields,grid,url
        except Exception as exc:
            logging.warning('RTMA %s unavailable: %s',run.isoformat(),exc);failures.append(str(exc));path.unlink(missing_ok=True)
    raise RuntimeError('No recent complete RTMA analysis: '+'; '.join(failures))


def number(value,low,high):
    try:
        value=float(value)
        return value if np.isfinite(value) and low<=value<=high else None
    except (ValueError,TypeError):return None


def parse_metars(text,now,run,usa=None):
    rows=csv.reader(io.StringIO(text));header=next(rows)
    if not {'station_id','observation_time','latitude','longitude','raw_text'}<=set(header):raise ValueError('Invalid METAR CSV headers')
    sky_indices=[i for i,key in enumerate(header) if key=='sky_cover']
    stations={};cover={'CLR':0,'SKC':0,'CAVOK':0,'FEW':.125,'SCT':.375,'BKN':.75,'OVC':1,'OVX':1,'VV':1}
    for values in rows:
        if len(values)!=len(header):continue
        row=dict(zip(header,values));ident=row['station_id']
        try:observed=datetime.fromisoformat(row['observation_time'].replace('Z','+00:00'))
        except ValueError:continue
        if observed.tzinfo is None or observed>now+timedelta(minutes=5) or now-observed>timedelta(hours=2) or abs(observed-run)>timedelta(minutes=90):continue
        lat=number(row['latitude'],24,50);lon=number(row['longitude'],-125,-66)
        if lat is None or lon is None or len(ident)!=4 or not ident.isalnum():continue
        if usa is not None and not intersects_xy(usa,lon,lat):continue
        if ident in stations and stations[ident]['observation_time']>=observed.isoformat():continue
        sky=[cover[values[i]] for i in sky_indices if values[i] in cover]
        station=dict(id=ident,latitude=lat,longitude=lon,observation_time=observed.isoformat(),
            temperature_c=number(row.get('temp_c'),-100,65),dewpoint_c=number(row.get('dewpoint_c'),-110,50),
            wind_direction=number(row.get('wind_dir_degrees'),0,360),wind_kt=number(row.get('wind_speed_kt'),0,180),
            gust_kt=number(row.get('wind_gust_kt'),0,200),slp_hpa=number(row.get('sea_level_pressure_mb'),850,1100),
            altimeter_inhg=number(row.get('altim_in_hg'),24,34),visibility_sm=number(row.get('visibility_statute_mi'),0,100),
            sky_fraction=max(sky) if sky else None,weather=row.get('wx_string') or None,raw=row['raw_text'])
        if station['temperature_c'] is None and station['wind_kt'] is None:continue
        stations[ident]=station
    return sorted(stations.values(),key=lambda s:s['id'])


def fetch_metars(http,cache,now,run,usa):
    path=Path(cache)/'metars.csv.gz';download(http,METARS,path,maximum=4_000_000)
    with gzip.open(path,'rb') as handle:payload=handle.read(12_000_001)
    if len(payload)>12_000_000:raise ValueError('Oversized METAR cache')
    result=parse_metars(payload.decode('utf-8-sig'),now,run,usa)
    if len(result)<100:raise ValueError('Too few recent CONUS stations to publish')
    return result


def humidity(temperature,dewpoint):
    t=temperature-273.15;d=dewpoint-273.15
    return np.clip(100*np.exp(17.625*d/(243.04+d)-17.625*t/(243.04+t)),0,100)
