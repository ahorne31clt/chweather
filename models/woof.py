"""Bounded inventory/range adapter for Recast's public WOOF-NAM pilot."""
from datetime import datetime,timedelta
from pathlib import Path
import re
from .data import read_frame,ADDITIONAL
BASE='https://woof-nam.recastsystems.com/'
PROFILE_LEVELS=list(range(1000,499,-25))
FIELDS=[('PRMSL','mean sea level'),('HGT','500 mb'),('HGT','1000 mb'),('TMP','2 m above ground'),('DPT','2 m above ground'),('RH','2 m above ground'),('UGRD','10 m above ground'),('VGRD','10 m above ground'),('UGRD','500 mb'),('VGRD','500 mb'),('ABSV','500 mb'),('CAPE','surface')]

from .diagnostics_data import FIELDS as DIAGNOSTICS
FIELDS=list(dict.fromkeys(FIELDS+DIAGNOSTICS+[('REFC','entire atmosphere (considered as a single layer)'),('PRES','surface')]+[(v,f'{level} mb') for level in PROFILE_LEVELS for v in ('TMP','HGT')]))

def cycles(http,now):
    response=http.get(BASE+'status.json',timeout=(15,30));response.raise_for_status()
    if len(response.content)>100000:raise ValueError('Oversized WOOF status')
    result=[]
    for item in response.json().get('cycles',[]):
        cycle=datetime.fromisoformat(item['cycle'].replace('Z','+00:00'))
        if item.get('state')=='complete' and item.get('hours_available',-1)>=84 and timedelta(0)<=now-cycle<=timedelta(days=2) and cycle>=datetime.fromisoformat('2026-11-05T06:00:00+00:00'):
            result.append(cycle)
    if not result:raise ValueError('No current compatible WOOF-NAM pilot cycle available')
    return sorted(set(result),reverse=True)[:2]

def ranges(text,requested=None):
    rows=[]
    for line in text.splitlines():
        cells=line.split(':')
        if len(cells)<6 or not cells[0].isdigit() or not cells[1].isdigit():raise ValueError('Invalid WOOF inventory')
        rows.append((int(cells[1]),cells))
    if not 100<len(rows)<2000 or any(b[0]<=a[0] for a,b in zip(rows,rows[1:])):raise ValueError('Invalid inventory offsets')
    selected=[]
    for variable,level in (FIELDS if requested is None else requested):
        hits=[i for i,(_,c) in enumerate(rows) if c[3]==variable and c[4]==level and ('acc' not in c[5] and 'max' not in c[5] and 'min' not in c[5])]
        if len(hits)!=1 or hits[0]+1>=len(rows):raise ValueError('Missing/ambiguous WOOF field '+variable+' '+level)
        i=hits[0];start,end=rows[i][0],rows[i+1][0]-1
        if not 0<end-start<6000000:raise ValueError('Unbounded field size')
        selected.append((start,end))
    combined=[]
    for start,end in sorted(selected):
        if combined and start==combined[-1][1]+1:combined[-1]=(combined[-1][0],end)
        else:combined.append((start,end))
    return combined

def fetch(http,cache,run,hour):
    if run.hour not in (0,6,12,18) or not 0<=hour<=84:raise ValueError('Invalid WOOF run/hour')
    url=BASE+f'woof-nam/12km/{run:%Y%m%d}/{run:%H}z/woof-nam.t{run:%H}z.awphys{hour:02d}.tm00.grib2'
    path=Path(cache)/f'woofnam-{run:%Y%m%d%H}-f{hour:03d}-fields-v2.grib2'
    if not path.exists():
        index=http.get(url+'.idx',timeout=(15,30));index.raise_for_status()
        if len(index.content)>500000:raise ValueError('Oversized WOOF inventory')
        download_ranges(http,url,path,ranges(index.text))
    import eccodes as ec
    with path.open('rb') as handle:
        while (gid:=ec.codes_grib_new_from_file(handle)) is not None:
            try:
                if ec.codes_get(gid,'generatingProcessIdentifier')!=254:raise ValueError('Unexpected WOOF generating process')
            finally:ec.codes_release(gid)
    expected=ADDITIONAL|{'pressure','height500','height1000','u10','v10','humidity2','cape'}
    expected|={'cin','gust','temperature850','u850','v850','temperature700','reflectivity','surface_pressure'}|{'temperature'+str(p) for p in PROFILE_LEVELS}|{'height'+str(p) for p in PROFILE_LEVELS}
    try:fields,grid=read_frame(path,'nam',run,hour,expected)
    except Exception:
        try:path.unlink(missing_ok=True)
        except OSError:pass
        raise
    if (grid['rows'],grid['cols'])!=(428,614):raise ValueError('Unexpected WOOF grid')
    from .winter import diagnose_type
    fields['diagnosed_type']=diagnose_type(fields,PROFILE_LEVELS)
    return fields,grid,url,path.stat().st_size


def download_ranges(http,url,path,selected):
    payload=bytearray()
    for start,end in selected:
        response=http.get(url,headers={'Range':f'bytes={start}-{end}'},timeout=(15,60),stream=True)
        with response:
            response.raise_for_status()
            if response.status_code!=206 or response.headers.get('Content-Range','').split('/')[0]!=f'bytes {start}-{end}':raise ValueError('Server ignored HTTP Range')
            data=bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data)>end-start+1:raise ValueError('Oversized GRIB range')
            if len(data)!=end-start+1 or data[:4]!=b'GRIB' or data[-4:]!=b'7777':raise ValueError('Incomplete GRIB range')
            payload.extend(data)
    temporary=path.with_suffix('.part');temporary.write_bytes(payload);temporary.replace(path)
