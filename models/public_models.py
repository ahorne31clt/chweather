"""Inventory-selected public operational RRFS and ECMWF IFS adapters."""
from pathlib import Path
import json,numpy as np
from .data import read_frame,REQUIRED,ADDITIONAL
from .woof import ranges,download_ranges
from .diagnostics_data import FIELDS as EXTRA

def rrfs_url(run,hour,kind):
    return f'https://noaa-rrfs-ops-pds.s3.amazonaws.com/rrfs.{run:%Y%m%d}/{run:%H}/rrfs.t{run:%H}z.{kind}.3km.f{hour:03d}.conus.grib2'

def fetch_public(http,cache,model,run,hour):
    path=Path(cache)/f'{model}-{run:%Y%m%d%H}-f{hour:03d}-public-v1.grib2'
    if model=='rrfs':
        url=rrfs_url(run,hour,'2dfld')
        if not path.exists():
            groups=[('2dfld',[('MSLET','mean sea level'),('TMP','2 m above ground'),('DPT','2 m above ground'),('RH','2 m above ground'),('UGRD','10 m above ground'),('VGRD','10 m above ground'),('PRATE','surface'),('CRAIN','surface'),('CSNOW','surface'),('CFRZR','surface'),('CICEP','surface'),('CAPE','surface'),('CIN','surface'),('GUST','surface'),('REFC','entire atmosphere (considered as a single layer)')]),('prslev',[('HGT','500 mb'),('HGT','1000 mb'),('UGRD','500 mb'),('VGRD','500 mb'),('ABSV','500 mb'),('TMP','850 mb'),('UGRD','850 mb'),('VGRD','850 mb')])]
            payload=bytearray()
            for kind,requested in groups:
                source=rrfs_url(run,hour,kind);r=http.get(source+'.idx',timeout=(15,30));r.raise_for_status()
                if len(r.content)>1000000:raise ValueError('Oversized RRFS inventory')
                part=path.with_suffix('.partgrib');download_ranges(http,source,part,ranges(r.text,requested));payload.extend(part.read_bytes());part.unlink()
            path.write_bytes(payload)
        required=REQUIRED|ADDITIONAL|{'u10','v10','humidity2','cape','cin','gust','reflectivity','temperature850','u850','v850'}
    else:
        url=f'https://data.ecmwf.int/forecasts/{run:%Y%m%d}/{run:%H}z/ifs/0p25/oper/{run:%Y%m%d%H}0000-{hour}h-oper-fc.grib2'
        desired=[('2t',None),('2d',None),('10u',None),('10v',None),('msl',None),('gh','500'),('gh','1000'),('u','500'),('v','500'),('vo','500'),('t','850'),('u','850'),('v','850'),('mucape',None),('ptype',None),('tprate',None)]
        if not path.exists():
            r=http.get(url.removesuffix('.grib2')+'.index',timeout=(15,30));r.raise_for_status()
            if len(r.content)>2000000:raise ValueError('Oversized ECMWF index')
            rows=[json.loads(line) for line in r.text.splitlines() if line.strip()];selected=[]
            for variable,level in desired:
                found=[x for x in rows if x['param']==variable and (x.get('levelist')==level if level else x.get('levtype')=='sfc')]
                if len(found)!=1:raise ValueError('Missing/ambiguous ECMWF '+variable+' '+str(level))
                item=found[0];start=int(item['_offset']);size=int(item['_length'])
                if not 0<size<3000000 or start<0:raise ValueError('Invalid ECMWF field size')
                selected.append((start,start+size-1))
            download_ranges(http,url,path,sorted(selected))
        required={'temperature2','dewpoint2','u10','v10','pressure','height500','height1000','u500','v500','vorticity500','temperature850','u850','v850','mucape','ecmwf_type','rate'}
    try:fields,grid=read_frame(path,model,run,hour,required)
    except Exception:
        try:path.unlink(missing_ok=True)
        except OSError:pass
        raise
    if model=='ecmwf':
        t=fields['temperature2']-273.15;td=fields['dewpoint2']-273.15
        fields['humidity2']=np.clip(100*np.exp(17.625*td/(243.04+td)-17.625*t/(243.04+t)),0,100)
        fields['vorticity500']+=2*7.292115e-5*np.sin(np.deg2rad(grid['latitudes']))[:,None]
        code=fields['ecmwf_type']
        fields.update(rain=np.isin(code,[1,2,11]).astype('float32'),snow=np.isin(code,[5,6]).astype('float32'),freezing_rain=np.isin(code,[3,12]).astype('float32'),sleet=(code==8).astype('float32'))
        fields['rain'][code==7]=1;fields['snow'][code==7]=1
    return fields,grid,url,path.stat().st_size
