from datetime import timedelta
from pathlib import Path
import re,threading
from concurrent.futures import ThreadPoolExecutor

import eccodes as ec
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOCAL=threading.local()
GRIB_LOCK=threading.Lock()
GEFS_MEMBERS=['c00']+[f'p{i:02d}' for i in range(1,31)]


def http():
    if not hasattr(LOCAL,'http'):
        LOCAL.http=requests.Session();LOCAL.http.headers['User-Agent']='CHWeatherEnsembles/1.0 (chweather.org)'
        LOCAL.http.mount('https://',HTTPAdapter(max_retries=Retry(total=2,backoff_factor=.5,status_forcelist=[429,500,502,503,504])))
    return LOCAL.http


def index(url,cache):
    path=Path(cache)
    if path.exists():text=path.read_text()
    else:
        r=http().get(url+'.idx',timeout=(10,30));r.raise_for_status();text=r.text
        if len(text)>300000:raise ValueError('Oversized GRIB index')
        path.write_text(text)
    rows=[]
    for line in text.splitlines():
        parts=line.split(':')
        if len(parts)<6 or not parts[1].isdigit():continue
        rows.append(dict(offset=int(parts[1]),line=line))
    if not rows or any(b['offset']<=a['offset'] for a,b in zip(rows,rows[1:])):raise ValueError('Invalid GRIB index')
    for i,row in enumerate(rows):row['end']=rows[i+1]['offset']-1 if i+1<len(rows) else None
    return rows


def record(url,row,path):
    path=Path(path)
    if path.exists():return path.read_bytes()
    a,b=row['offset'],row['end']
    if b is None or b-a>5_000_000:raise ValueError('Unbounded GRIB record')
    with http().get(url,headers={'Range':f'bytes={a}-{b}'},timeout=(10,45),stream=True) as response:
        response.raise_for_status()
        if response.status_code!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {a}-{b}/'):raise ValueError('Server ignored precise GRIB byte range')
        payload=bytearray()
        for chunk in response.iter_content(65536):
            payload.extend(chunk)
            if len(payload)>b-a+1:raise ValueError('Oversized GRIB range')
    if len(payload)!=b-a+1 or not payload.startswith(b'GRIB') or not payload.endswith(b'7777'):raise ValueError('Incomplete GRIB record')
    temp=path.with_suffix('.part');temp.write_bytes(payload);temp.replace(path)
    return bytes(payload)


def choose(rows,predicate):
    matches=[r for r in rows if predicate(r['line'])]
    if len(matches)!=1:raise ValueError(f'Expected one matching GRIB record; found {len(matches)}')
    return matches[0]


def decode(payload,run,hour):
    # ecCodes definition initialization is not thread-safe on every platform.
    # Downloads overlap, while all GRIB access stays serialized.
    with GRIB_LOCK:return _decode(payload,run,hour)


def _decode(payload,run,hour):
    g=ec.codes_new_from_message(payload)
    try:
        if ec.codes_get(g,'dataDate')!=int(run.strftime('%Y%m%d')) or ec.codes_get(g,'dataTime')!=run.hour*100 or ec.codes_get(g,'endStep')!=hour:raise ValueError('Ensemble run or lead mismatch')
        grid=dict(type=ec.codes_get(g,'gridType'),rows=ec.codes_get(g,'Nj'),cols=ec.codes_get(g,'Ni'),id=ec.codes_get(g,'md5GridSection'))
        values=ec.codes_get_values(g).reshape(grid['rows'],grid['cols']).astype('float32')
        if ec.codes_get(g,'numberOfMissing'):values[values==ec.codes_get(g,'missingValue')]=np.nan
        if grid['type']=='regular_ll':
            lat=ec.codes_get_array(g,'latitudes').reshape(values.shape)[:,0];lon=(ec.codes_get_array(g,'longitudes').reshape(values.shape)[0]+180)%360-180
            iy=np.where((lat>=24)&(lat<=50))[0];ix=np.where((lon>=-125)&(lon<=-66))[0]
            iy=iy[np.argsort(lat[iy])];ix=ix[np.argsort(lon[ix])];values=values[np.ix_(iy,ix)]
            grid.update(latitudes=lat[iy],longitudes=lon[ix])
        elif grid['type']=='lambert':
            for out,key in [('first_lat','latitudeOfFirstGridPointInDegrees'),('first_lon','longitudeOfFirstGridPointInDegrees'),('j_positive','jScansPositively'),('i_negative','iScansNegatively'),('earth_radius','radius'),('central_lon','LoVInDegrees'),('central_lat','LaDInDegrees'),('parallel1','Latin1InDegrees'),('parallel2','Latin2InDegrees'),('dx','DxInMetres'),('dy','DyInMetres')]:grid[out]=ec.codes_get(g,key)
        else:raise ValueError('Unsupported ensemble grid')
        attrs={k:ec.codes_get(g,k) for k in ['shortName','typeOfLevel','level','topLevel','bottomLevel','units','stepType','startStep','endStep','perturbationNumber','totalNumberOfForecastProbabilities','probabilityType','scaledValueOfLowerLimit','scaleFactorOfLowerLimit','scaledValueOfUpperLimit','scaleFactorOfUpperLimit'] if ec.codes_is_defined(g,k)}
        return values,grid,attrs
    finally:ec.codes_release(g)


def gefs_member(cache,run,hour,member):
    url=f'https://noaa-gefs-pds.s3.amazonaws.com/gefs.{run:%Y%m%d}/{run:%H}/atmos/pgrb2ap5/ge{member}.t{run:%H}z.pgrb2a.0p50.f{hour:03d}'
    prefix=Path(cache)/f'gefs-{run:%Y%m%d%H}-{member}-f{hour:03d}'
    rows=index(url,str(prefix)+'.idx');result={};grid=None
    for name,needle in [('temperature',':TMP:2 m above ground:'),('precipitation',':APCP:surface:')]:
        row=choose(rows,lambda line:needle in line)
        values,current,attrs=decode(record(url,row,str(prefix)+'-'+name+'.grib2'),run,hour)
        if attrs.get('perturbationNumber')!=int(member[1:]):raise ValueError('GEFS member identifier mismatch')
        if grid is not None and grid['id']!=current['id']:raise ValueError('GEFS grids differ')
        grid=current
        if name=='temperature':
            if attrs['shortName']!='2t' or attrs['typeOfLevel']!='heightAboveGround' or attrs['level']!=2 or attrs['units']!='K' or attrs['stepType']!='instant' or not np.isfinite(values).all() or values.min()<150 or values.max()>350:raise ValueError('Invalid GEFS temperature')
        else:
            if attrs['shortName']!='tp' or attrs['typeOfLevel']!='surface' or attrs['units']!='kg m**-2' or attrs['stepType']!='accum' or attrs['startStep']!=hour-6 or not np.isfinite(values).all() or values.min()<0 or values.max()>2000:raise ValueError('GEFS precipitation must cover exactly the preceding six hours')
        if grid['type']!='regular_ll' or not np.allclose(np.diff(grid['latitudes']),.5) or not np.allclose(np.diff(grid['longitudes']),.5):raise ValueError('Unexpected GEFS source grid')
        result[name]=values
    return result,grid,url


def probability(values,threshold,operator,expected_members):
    values=np.asarray(values)
    if values.shape[0]!=expected_members or not np.isfinite(values).all():raise ValueError('All expected ensemble members must be present and finite')
    test={'lt':np.less,'gt':np.greater,'ge':np.greater_equal}[operator]
    return 100*np.count_nonzero(test(values,threshold),axis=0)/expected_members


def gefs_frame(cache,run,hour):
    with ThreadPoolExecutor(max_workers=4) as pool:members=list(pool.map(lambda m:gefs_member(cache,run,hour,m),GEFS_MEMBERS))
    if len({m[1]['id'] for m in members})!=1:raise ValueError('GEFS member grids differ')
    temperatures=np.stack([m[0]['temperature'] for m in members]);rain=np.stack([m[0]['precipitation'] for m in members])
    result={'freeze':probability(temperatures,273.15,'lt',31),'hot90':probability(temperatures,(90-32)/1.8+273.15,'gt',31)}
    for id,threshold in [('rain01',2.54),('rain05',12.7),('rain1',25.4)]:result[id]=probability(rain,threshold,'ge',31)
    return result,members[0][1],dict(member_count=31,member_ids=GEFS_MEMBERS,source_urls=[m[2] for m in members],probability_kind='Uncalibrated pointwise member fraction')


def refs_frame(cache,run,hour):
    url=f'https://noaa-rrfs-ops-pds.s3.amazonaws.com/refs.{run:%Y%m%d}/{run:%H}/ensprod/refs.t{run:%H}z.prob.f{hour:02d}.conus.grib2'
    prefix=Path(cache)/f'refs-{run:%Y%m%d%H}-f{hour:03d}';rows=index(url,str(prefix)+'.idx')
    result={};grid=None;count=None
    specs=[('freeze',lambda l:':TMP:2 m above ground:' in l and ':prob <273.15:' in l,'2t','K',0,273.15,False),
           ('cape1000',lambda l:':CAPE:90-0 mb above ground:' in l and ':prob >1000:' in l,'cape','J kg**-1',1,1000,False),
           ('rain1',lambda l:':APCP:surface:' in l and f':{hour-6}-{hour} hour acc fcst:' in l and ':prob >25.4:' in l and 'Neighborhood Probability' in l,'tp','kg m**-2',1,25.4,True)]
    for name,predicate,short,units,kind,threshold,accum in specs:
        row=choose(rows,predicate);values,current,attrs=decode(record(url,row,str(prefix)+'-'+name+'.grib2'),run,hour)
        limit='Lower' if kind==0 else 'Upper'
        actual=attrs[f'scaledValueOf{limit}Limit']*10**(-attrs[f'scaleFactorOf{limit}Limit'])
        if attrs['shortName']!=short or attrs['units']!=units or attrs.get('probabilityType')!=kind or not np.isclose(actual,threshold,atol=.0001):raise ValueError('REFS probability variable or threshold mismatch')
        if name=='freeze' and (attrs['typeOfLevel']!='heightAboveGround' or attrs['level']!=2):raise ValueError('REFS freezing probability must be at 2 m')
        if name=='cape1000' and (attrs['typeOfLevel']!='pressureFromGroundLayer' or attrs['topLevel']!=9000 or attrs['bottomLevel']!=0):raise ValueError('REFS CAPE must use the lowest 90 mb')
        if name=='rain1' and attrs['typeOfLevel']!='surface':raise ValueError('REFS precipitation must be at the surface')
        if current['type']!='lambert' or current['dx']!=3000 or current['dy']!=3000:raise ValueError('Unexpected REFS source grid')
        if attrs['stepType']!=('accum' if accum else 'instant') or (accum and attrs['startStep']!=hour-6):raise ValueError('REFS probability interval mismatch')
        member_count=attrs.get('totalNumberOfForecastProbabilities')
        if not isinstance(member_count,int) or not 2<=member_count<=30:raise ValueError('Invalid REFS member count')
        if count is not None and count!=member_count:raise ValueError('REFS fields have inconsistent member counts')
        if grid and grid['id']!=current['id']:raise ValueError('REFS grids differ')
        if not np.isfinite(values).all() or values.min()<0 or values.max()>100:raise ValueError('Invalid REFS probability values')
        count=member_count;grid=current;result[name]=values
    return result,grid,dict(member_count=count,source_urls=[url],probability_kind='NOAA published probability; rainfall uses neighborhood processing')


def cycles(now):
    first=now-timedelta(hours=5);first=first.replace(hour=first.hour//6*6,minute=0,second=0,microsecond=0)
    return [first-timedelta(hours=6*i) for i in range(3)]
