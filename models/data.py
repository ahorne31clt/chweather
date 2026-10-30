from datetime import datetime, timedelta
from pathlib import Path
import logging

import eccodes as ec
import numpy as np
import requests

from sunset.data import download

LOG=logging.getLogger('models.data')
REQUIRED={'rain','snow','freezing_rain','sleet','rate','pressure','height500','height1000'}
ADDITIONAL={'temperature2','dewpoint2','u500','v500','vorticity500'}
SURFACE={'crain':'rain','csnow':'snow','cfrzr':'freezing_rain','cicep':'sleet','prate':'rate'}


def candidate_cycles(model,now,extended=False):
    ready=now-timedelta(hours=4 if model in ('gfs','nam') else 2)
    first=ready.replace(minute=0,second=0,microsecond=0)
    six_hourly=model in ('gfs','nam') or extended
    if six_hourly:first=first.replace(hour=first.hour//6*6)
    return [first-timedelta(hours=(6 if six_hourly else 1)*i) for i in range(3)]


def request_details(model,run,hour):
    query=dict(lev_surface='on',lev_mean_sea_level='on',lev_500_mb='on',lev_1000_mb='on',lev_2_m_above_ground='on')
    query.update({f'var_{name}':'on' for name in ['HGT','PRATE','CRAIN','CSNOW','CFRZR','CICEP',
                 'TMP','DPT','UGRD','VGRD','PRMSL' if model=='gfs' else 'MSLMA']+(['ABSV'] if model=='gfs' else [])})
    if model=='gfs':
        endpoint='https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl'
        query.update(dir=f'/gfs.{run:%Y%m%d}/{run:%H}/atmos',file=f'gfs.t{run:%H}z.pgrb2.0p25.f{hour:03d}',
                     subregion='',leftlon=228,rightlon=298,bottomlat=20,toplat=54)
    elif model=='nam':
        endpoint='https://nomads.ncep.noaa.gov/cgi-bin/filter_nam.pl'
        query={k:v for k,v in query.items() if k not in ['var_PRATE','var_CRAIN','var_CSNOW','var_CFRZR','var_CICEP','var_MSLMA']}
        query.update(var_PRMSL='on',var_ABSV='on',dir=f'/nam.{run:%Y%m%d}',file=f'nam.t{run:%H}z.awphys{hour:02d}.tm00.grib2')
    else:
        endpoint='https://nomads.ncep.noaa.gov/cgi-bin/filter_hrrr_2d.pl'
        query.update(dir=f'/hrrr.{run:%Y%m%d}/conus',file=f'hrrr.t{run:%H}z.wrfsfcf{hour:02d}.grib2')
    return endpoint,query


def fetch_frame(http,cache,model,run,hour):
    endpoint,query=request_details(model,run,hour)
    path=Path(cache)/f'{model}-{run:%Y%m%d%H}-f{hour:03d}-fields-v2.grib2'
    url=requests.Request('GET',endpoint,params=query).prepare().url
    if not path.exists():
        LOG.info('Download %s %s F%03d',model.upper(),run.isoformat(),hour)
        download(http,endpoint,path,params=query,maximum=30_000_000)
    expected=REQUIRED|ADDITIONAL
    if model=='nam':expected-={'rain','snow','freezing_rain','sleet','rate'}
    try:fields,grid=read_frame(path,model,run,hour,expected-{'vorticity500'} if model=='hrrr' else expected)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    size=path.stat().st_size
    if model=='hrrr':
        vort_path,vort_url=fetch_hrrr_vorticity(http,cache,run,hour)
        try:extra,vort_grid=read_frame(vort_path,model,run,hour,{'vorticity500'})
        except Exception:
            vort_path.unlink(missing_ok=True)
            raise
        if grid['id']!=vort_grid['id']:raise ValueError('HRRR vorticity grid differs from surface grid')
        fields.update(extra);size+=vort_path.stat().st_size
    extra,extra_grid,extra_size=fetch_surface_fields(http,cache,model,run,hour)
    if grid['id']!=extra_grid['id']:raise ValueError('Surface parameter grids differ from base model grid')
    fields.update(extra);size+=extra_size
    return fields,grid,url,size


def surface_request_details(model,run,hour):
    endpoint,query=request_details(model,run,hour)
    query={k:v for k,v in query.items() if not k.startswith(('var_','lev_'))}
    query.update(lev_2_m_above_ground='on',lev_10_m_above_ground='on',lev_surface='on',
                 var_UGRD='on',var_VGRD='on',var_RH='on',var_CAPE='on')
    return endpoint,query


def fetch_surface_fields(http,cache,model,run,hour):
    endpoint,query=surface_request_details(model,run,hour)
    path=Path(cache)/f'{model}-{run:%Y%m%d%H}-f{hour:03d}-surface-v1.grib2'
    if not path.exists():download(http,endpoint,path,params=query,maximum=20_000_000)
    try:fields,grid=read_frame(path,model,run,hour,{'u10','v10','humidity2','cape'})
    except Exception:
        path.unlink(missing_ok=True);raise
    return fields,grid,path.stat().st_size


def fetch_hrrr_vorticity(http,cache,run,hour):
    """Read exactly one GRIB record from NOAA's public HRRR archive."""
    url=f'https://noaa-hrrr-bdp-pds.s3.amazonaws.com/hrrr.{run:%Y%m%d}/conus/hrrr.t{run:%H}z.wrfprsf{hour:02d}.grib2'
    path=Path(cache)/f'hrrr-{run:%Y%m%d%H}-f{hour:03d}-absv.grib2'
    if path.exists():return path,url
    index=http.get(url+'.idx',timeout=(15,45));index.raise_for_status()
    if len(index.content)>500_000:raise ValueError('Oversized HRRR index')
    lines=index.text.splitlines();matches=[]
    for i,line in enumerate(lines[:-1]):
        if ':ABSV:500 mb:' in line:matches.append((int(line.split(':')[1]),int(lines[i+1].split(':')[1])-1))
    if len(matches)!=1:raise ValueError('Missing or ambiguous 500 mb HRRR absolute vorticity')
    start,end=matches[0]
    if not 0<end-start<5_000_000:raise ValueError('Invalid HRRR GRIB byte range')
    response=http.get(url,headers={'Range':f'bytes={start}-{end}'},timeout=(15,90),stream=True)
    temporary=path.with_suffix('.part')
    try:
        with response:
            response.raise_for_status()
            if response.status_code!=206 or response.headers.get('Content-Range','').split('/')[0]!=f'bytes {start}-{end}':
                raise ValueError('HRRR server did not honor the requested byte range')
            size=0
            with temporary.open('wb') as handle:
                for chunk in response.iter_content(65536):
                    size+=len(chunk)
                    if size>end-start+1:raise ValueError('Oversized HRRR vorticity response')
                    handle.write(chunk)
            if size!=end-start+1:raise ValueError('Incomplete HRRR vorticity response')
        temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)
    return path,url


def field_key(short,level_type,level,model):
    if level_type=='surface' and short=='cape':return 'cape'
    if level_type=='heightAboveGround' and level==10:
        if short in ('10u','u'):return 'u10'
        if short in ('10v','v'):return 'v10'
    if level_type=='heightAboveGround' and level==2:
        if short in ('2t','t'):return 'temperature2'
        if short in ('2d','dpt'):return 'dewpoint2'
        if short in ('2r','r'):return 'humidity2'
    if level_type=='isobaricInhPa' and level==500 and short in ('u','v','absv'):
        return {'u':'u500','v':'v500','absv':'vorticity500'}[short]
    if short in SURFACE and level_type=='surface':return SURFACE[short]
    if short=='gh' and level_type=='isobaricInhPa' and level in (500,1000):return 'height'+str(level)
    if short==('prmsl' if model in ('gfs','nam') else 'mslma') and level_type=='meanSea':return 'pressure'
    return None


def read_frame(path,model,run,hour,required=None):
    ec.codes_grib_multi_support_on()
    required=REQUIRED if required is None else required
    fields={};grid=None
    try:
        with Path(path).open('rb') as handle:
            while (gid:=ec.codes_grib_new_from_file(handle)) is not None:
                try:
                    if ec.codes_get(gid,'stepType')!='instant':continue
                    key=field_key(ec.codes_get(gid,'shortName'),ec.codes_get(gid,'typeOfLevel'),ec.codes_get(gid,'level'),model)
                    if key is None or key not in required:continue
                    if ec.codes_get(gid,'dataDate')!=int(run.strftime('%Y%m%d')) or ec.codes_get(gid,'dataTime')!=run.hour*100 or ec.codes_get(gid,'endStep')!=hour:
                        raise ValueError('Model run/lead does not match requested frame')
                    if ec.codes_get(gid,'validityDate')!=int((run+timedelta(hours=hour)).strftime('%Y%m%d')) or ec.codes_get(gid,'validityTime')!=(run+timedelta(hours=hour)).hour*100:
                        raise ValueError('Incorrect model valid time')
                    rows,cols=ec.codes_get(gid,'Nj'),ec.codes_get(gid,'Ni')
                    grid_id=ec.codes_get(gid,'md5GridSection')
                    if grid is None:
                        grid=dict(id=grid_id,rows=rows,cols=cols,type=ec.codes_get(gid,'gridType'),
                          first_lat=ec.codes_get(gid,'latitudeOfFirstGridPointInDegrees'),
                          first_lon=(ec.codes_get(gid,'longitudeOfFirstGridPointInDegrees')+180)%360-180,
                          j_positive=ec.codes_get(gid,'jScansPositively'),i_negative=ec.codes_get(gid,'iScansNegatively'),
                          earth_radius=ec.codes_get(gid,'radius'))
                        if model=='gfs':
                            if grid['type']!='regular_ll':raise ValueError('Unsupported GFS grid')
                            lat=ec.codes_get_array(gid,'latitudes').reshape(rows,cols)[:,0]
                            lon=(ec.codes_get_array(gid,'longitudes').reshape(rows,cols)[0,:]+180)%360-180
                            grid.update(latitudes=lat,longitudes=lon)
                        else:
                            if grid['type']!='lambert':raise ValueError('Unsupported HRRR grid')
                            for output,source in [('central_lon','LoVInDegrees'),('central_lat','LaDInDegrees'),
                                    ('parallel1','Latin1InDegrees'),('parallel2','Latin2InDegrees'),('dx','DxInMetres'),('dy','DyInMetres')]:
                                grid[output]=ec.codes_get(gid,source)
                            grid['central_lon']=(grid['central_lon']+180)%360-180
                    elif grid['id']!=grid_id:raise ValueError('Fields have inconsistent grid definitions')
                    if key in ('u500','v500'):
                        relative=int(ec.codes_get(gid,'uvRelativeToGrid'))
                        if 'wind_grid_relative' in grid and grid['wind_grid_relative']!=relative:raise ValueError('Inconsistent wind vector orientation')
                        grid['wind_grid_relative']=relative
                    if key in fields:raise ValueError('Duplicate instantaneous model field: '+key)
                    values=ec.codes_get_values(gid).reshape(rows,cols).astype(np.float32)
                    if ec.codes_get(gid,'numberOfMissing'):
                        values[values==ec.codes_get(gid,'missingValue')]=np.nan
                    if np.isfinite(values).sum()<values.size*.8:raise ValueError('Excessive missing model data')
                    good=values[np.isfinite(values)]
                    if key in ['rain','snow','freezing_rain','sleet']:
                        if good.min()<0 or good.max()>1:raise ValueError('Precipitation flags outside 0/1 range')
                    elif key=='rate':
                        if ec.codes_get(gid,'units')!='kg m**-2 s**-1' or good.min()<0 or good.max()>1:
                            raise ValueError('Unexpected precipitation rate units/range')
                    elif key=='pressure':
                        if ec.codes_get(gid,'units')!='Pa' or good.min()<70000 or good.max()>115000:
                            raise ValueError('Unexpected mean-sea-level pressure units/range')
                    elif key in ('temperature2','dewpoint2'):
                        if ec.codes_get(gid,'units')!='K' or good.min()<150 or good.max()>350:
                            raise ValueError('Unexpected 2 m temperature/dewpoint units or range')
                    elif key=='humidity2':
                        if ec.codes_get(gid,'units')!='%' or good.min()<0 or good.max()>100.1:raise ValueError('Invalid 2 m relative humidity')
                    elif key=='cape':
                        if ec.codes_get(gid,'units') not in ('J kg**-1','J/kg') or good.min()<0 or good.max()>50000:raise ValueError('Invalid surface-based CAPE')
                    elif key in ('u500','v500','u10','v10'):
                        if ec.codes_get(gid,'units') not in ('m s**-1','m/s') or np.abs(good).max()>200:
                            raise ValueError('Unexpected 500 mb wind units/range')
                    elif key=='vorticity500':
                        if ec.codes_get(gid,'units') not in ('s**-1','1/s') or np.abs(good).max()>.05:
                            raise ValueError('Unexpected 500 mb absolute vorticity units/range')
                    elif ec.codes_get(gid,'units') not in ('gpm','m'):
                        raise ValueError('Unexpected geopotential-height units')
                    fields[key]=values
                finally:ec.codes_release(gid)
    except ec.CodesInternalError as exc:raise ValueError('Malformed model GRIB response') from exc
    if set(fields)!=required:raise ValueError('Missing instantaneous model fields: '+str(sorted(required-set(fields))))
    if {'height500','height1000'}<=set(fields):
        thickness=(fields['height500']-fields['height1000'])/10
        if np.nanmin(thickness)<300 or np.nanmax(thickness)>700:raise ValueError('Implausible 1000–500 mb thickness')
    if model=='gfs':
        lat_order=np.argsort(grid['latitudes']);lon_order=np.argsort(grid['longitudes'])
        grid['latitudes']=grid['latitudes'][lat_order];grid['longitudes']=grid['longitudes'][lon_order]
        fields={key:values[np.ix_(lat_order,lon_order)] for key,values in fields.items()}
    return fields,grid
