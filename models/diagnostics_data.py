"""Bounded added-field downloads; HRRR reads inventory-selected records."""
from pathlib import Path
from .data import request_details,read_frame
from sunset.data import download
FIELDS=[('CIN','surface'),('GUST','surface'),('TMP','850 mb'),('UGRD','850 mb'),('VGRD','850 mb')]
KEYS={'cin','gust','temperature850','u850','v850'}

def fetch_diagnostics(http,cache,model,run,hour):
    path=Path(cache)/f'{model}-{run:%Y%m%d%H}-f{hour:03d}-diagnostics-v1.grib2'
    keys=set(KEYS)
    if model=='hrrr':keys.add('reflectivity')
    if not path.exists():
        if model=='hrrr':
            from .woof import ranges,download_ranges
            url=f'https://noaa-hrrr-bdp-pds.s3.amazonaws.com/hrrr.{run:%Y%m%d}/conus/hrrr.t{run:%H}z.wrfsfcf{hour:02d}.grib2'
            r=http.get(url+'.idx',timeout=(15,30));r.raise_for_status()
            if len(r.content)>500000:raise ValueError('Oversized diagnostic index')
            download_ranges(http,url,path,ranges(r.text,FIELDS+[('REFC','entire atmosphere')]))
        else:
            endpoint,query=request_details(model,run,hour)
            query={k:v for k,v in query.items() if not k.startswith(('lev_','var_'))}
            query.update(lev_surface='on',lev_850_mb='on')
            query.update({f'var_{v}':'on' for v in ('CIN','GUST','TMP','DPT','UGRD','VGRD')})
            download(http,endpoint,path,params=query,maximum=25000000)
    try:fields,grid=read_frame(path,model,run,hour,keys)
    except Exception:
        try:path.unlink(missing_ok=True)
        except OSError:pass
        raise
    return fields,grid,path.stat().st_size
