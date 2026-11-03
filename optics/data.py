"""Small NOAA GFS subsets with strict run, interval, units and grid validation."""
from datetime import timedelta
from pathlib import Path
import numpy as np
import eccodes as ec
from sunset.data import download,FILTER


def cycles(now):
    ready=now-timedelta(hours=5)
    first=ready.replace(hour=ready.hour//6*6,minute=0,second=0,microsecond=0)
    return [first-timedelta(hours=6*i) for i in range(3)]


def read(path,run,hour):
    fields={};axes=None
    mapping={'lcc':'low','mcc':'middle','hcc':'high','vis':'visibility','prate':'rate','crain':'rain'}
    with Path(path).open('rb') as f:
        while (g:=ec.codes_grib_new_from_file(f)) is not None:
            try:
                short=ec.codes_get(g,'shortName');level=ec.codes_get(g,'level');typ=ec.codes_get(g,'typeOfLevel')
                key=mapping.get(short)
                if typ=='isobaricInhPa' and level in (300,400,500):
                    key={'t':'temp','r':'rh','icmr':'ice','ciwmr':'ice'}.get(short)
                    if key:key+=str(level)
                if key is None or ec.codes_get(g,'stepType')!='instant':continue
                if (ec.codes_get(g,'dataDate'),ec.codes_get(g,'dataTime'),ec.codes_get(g,'endStep'))!=(int(run.strftime('%Y%m%d')),run.hour*100,hour):raise ValueError('Optics GRIB timing mismatch')
                unit=ec.codes_get(g,'units');expected='K' if key.startswith('temp') else '%' if key.startswith('rh') or key in ('low','middle','high') else 'kg kg**-1' if key.startswith('ice') else 'm' if key=='visibility' else 'kg m**-2 s**-1' if key=='rate' else '(Code table 4.222)'
                if key=='rain':
                    if unit not in ('(Code table 4.222)','Proportion','Numeric','(Code table 4.201)'):raise ValueError('Unexpected rain flag units: '+unit)
                elif unit!=expected:raise ValueError('Unexpected '+key+' units: '+unit)
                ny,nx=ec.codes_get(g,'Nj'),ec.codes_get(g,'Ni')
                if ec.codes_get(g,'alternativeRowScanning') or ec.codes_get(g,'jPointsAreConsecutive'):raise ValueError('Unsupported GFS scan')
                lat=ec.codes_get_array(g,'latitudes').reshape(ny,nx)[:,0];lon=(ec.codes_get_array(g,'longitudes').reshape(ny,nx)[0]+180)%360-180
                values=ec.codes_get_values(g).reshape(ny,nx)
                if ec.codes_get(g,'bitmapPresent') or not np.isfinite(values).all():raise ValueError('Missing optics input')
                if lat[0]>lat[-1]:lat=lat[::-1];values=values[::-1]
                if not np.allclose(np.diff(lat),.25) or not np.allclose(np.diff(lon),.25):raise ValueError('Unexpected GFS grid spacing')
                if axes is not None and (not np.array_equal(lat,axes[0]) or not np.array_equal(lon,axes[1])):raise ValueError('GFS optics grids differ')
                axes=(lat,lon)
                if key in fields:raise ValueError('Duplicate optics input '+key)
                if key in ('low','middle','high') or key.startswith('rh'):
                    if values.min()<0 or values.max()>100.01:raise ValueError('Invalid percentage')
                if key.startswith('temp') and (values.min()<150 or values.max()>340):raise ValueError('Invalid temperature')
                if (key.startswith('ice') or key in ('rate','rain','visibility')) and values.min()<0:raise ValueError('Negative physical input')
                fields[key]=values
            finally:ec.codes_release(g)
    required=set(mapping.values())|{k+str(p) for k in ('temp','rh','ice') for p in (300,400,500)}
    if fields.keys()!=required:raise ValueError('Missing optics fields: '+str(required-fields.keys()))
    return fields,axes


def fetch(http,cache,run,hour):
    query=dict(dir=f'/gfs.{run:%Y%m%d}/{run:%H}/atmos',file=f'gfs.t{run:%H}z.pgrb2.0p25.f{hour:03d}',subregion='',leftlon=228,rightlon=298,bottomlat=20,toplat=54)
    query.update({f'var_{k}':'on' for k in ('LCDC','MCDC','HCDC','VIS','PRATE','CRAIN','TMP','RH','ICMR')})
    query.update({f'lev_{k}':'on' for k in ('low_cloud_layer','middle_cloud_layer','high_cloud_layer','surface','300_mb','400_mb','500_mb')})
    path=Path(cache)/f'gfs-{run:%Y%m%d%H}-{hour:03d}.grib2'
    if not path.exists():download(http,FILTER,path,params=query,maximum=15_000_000)
    import requests
    try:fields,axes=read(path,run,hour)
    except Exception:path.unlink(missing_ok=True);raise
    return fields,axes,requests.Request('GET',FILTER,params=query).prepare().url
