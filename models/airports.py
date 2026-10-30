"""Publish model-consistent CONUS airport meteograms: python -m models.airports."""
from pathlib import Path
from datetime import datetime,timezone
import csv
import hashlib
import json
import logging
import os
import tempfile
import time

import numpy as np
import cartopy.crs as ccrs

from sunset.data import session,download
from .data import request_details,read_frame
from .render import projection_for,native_axes

ROOT=Path(__file__).resolve().parent.parent
CATALOG_URL='https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv'
LOG=logging.getLogger('models.airports')
CHUNK_SIZE=128


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def airport_catalog(http,cache):
    path=cache/'airports.csv'
    if not path.exists() or time.time()-path.stat().st_mtime>86400:
        download(http,CATALOG_URL,path,maximum=20_000_000)
    airports=[]
    with path.open(encoding='utf-8-sig',newline='') as handle:
        for row in csv.DictReader(handle):
            if row['iso_country']!='US' or row['type'] not in ('small_airport','medium_airport','large_airport'):continue
            lat,lon=float(row['latitude_deg']),float(row['longitude_deg'])
            if not (23.5<=lat<=50.5 and -126<=lon<=-65):continue
            icao=row.get('icao_code') or row.get('gps_code') or ''
            airports.append(dict(id=row['ident'],icao=icao,iata=row.get('iata_code',''),local=row.get('local_code',''),
                name=row['name'],city=row.get('municipality',''),state=row.get('iso_region','').removeprefix('US-'),
                lat=lat,lon=lon,type=row['type']))
    airports.sort(key=lambda a:a['id'])
    if len(airports)<1000 or len({a['id'] for a in airports})!=len(airports):raise ValueError('Invalid airport catalog')
    return airports,datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(timespec='seconds')


def nearest_indices(axis,values):
    ascending=axis[-1]>axis[0];ordered=axis if ascending else axis[::-1]
    right=np.clip(np.searchsorted(ordered,values),1,len(ordered)-1);left=right-1
    index=np.where(abs(values-ordered[left])<=abs(values-ordered[right]),left,right)
    valid=(values>=ordered[0])&(values<=ordered[-1])&np.isfinite(values)
    return (index if ascending else len(axis)-1-index),valid


def airport_indices(grid,airports):
    lon=np.array([a['lon'] for a in airports]);lat=np.array([a['lat'] for a in airports])
    if grid['type']=='lambert':
        projection=projection_for(grid);x,y=native_axes(grid,projection)
        points=projection.transform_points(ccrs.PlateCarree(),lon,lat);px,py=points[:,0],points[:,1]
    else:x,y=grid['longitudes'],grid['latitudes'];px,py=lon,lat
    cols,vx=nearest_indices(x,px);rows,vy=nearest_indices(y,py)
    return rows,cols,vx&vy


def wind_frame(http,cache,model,cycle,hour):
    combined=cache/f'{model}-{cycle:%Y%m%d%H}-f{hour:03d}-surface-v1.grib2'
    if combined.exists():
        fields,grid=read_frame(combined,model,cycle,hour,{'u10','v10'})
        return fields,grid,False
    path=cache/f'{model}-{cycle:%Y%m%d%H}-f{hour:03d}-wind10.grib2'
    endpoint,query=request_details(model,cycle,hour)
    query={k:v for k,v in query.items() if not k.startswith(('var_','lev_'))}
    query.update(lev_10_m_above_ground='on',var_UGRD='on',var_VGRD='on')
    downloaded=not path.exists()
    if downloaded:download(http,endpoint,path,params=query,maximum=12_000_000)
    try:fields,grid=read_frame(path,model,cycle,hour,{'u10','v10'})
    except Exception:
        path.unlink(missing_ok=True);raise
    return fields,grid,downloaded


def airport_values(fields,wind,indices):
    rows,cols,valid=indices
    temp=(fields['temperature2'][rows,cols]-273.15)*1.8+32
    speed=np.hypot(wind['u10'][rows,cols],wind['v10'][rows,cols])*1.94384449244
    rate=fields['rate'][rows,cols]*3600
    values=np.stack([temp,speed,rate],axis=-1).astype('<f4')
    values[~valid]=np.nan
    return values


def generate():
    source=ROOT/'generated/models/latest.json'
    manifest=json.loads(source.read_text(encoding='utf-8'))
    output=ROOT/'generated/models/airports';output.mkdir(parents=True,exist_ok=True)
    cache=ROOT/'.cache/models';cache.mkdir(parents=True,exist_ok=True)
    with session() as http,tempfile.TemporaryDirectory(dir=output) as staging:
        staging=Path(staging);airports,catalog_time=airport_catalog(http,cache)
        catalog=staging/'catalog.json';catalog.write_text(json.dumps(airports,separators=(',',':'),allow_nan=False),encoding='utf-8')
        products=[];keep={'catalog.json','latest.json'}
        for model in manifest['models']:
            if model['status']!='available' or model['id']=='nam':continue
            cycle=datetime.fromisoformat(model['model_run'].replace('Z','+00:00'))
            values=[];indices=None;grid_id=None
            for frame in model['frames']:
                hour=frame['hour']
                path=cache/f'{model["id"]}-{cycle:%Y%m%d%H}-f{hour:03d}-fields-v2.grib2'
                fields,grid=read_frame(path,model['id'],cycle,hour,{'temperature2','rate'})
                wind,wgrid,downloaded=wind_frame(http,cache,model['id'],cycle,hour)
                if grid['id']!=wgrid['id']:raise ValueError('Airport temperature and wind grids differ')
                if indices is None:indices=airport_indices(grid,airports);grid_id=grid['id']
                elif grid_id!=grid['id']:raise ValueError('Airport model grid changed within cycle')
                values.append(airport_values(fields,wind,indices))
                LOG.info('%s airport forecast F%03d / %d airports',model['name'],hour,len(airports))
                if downloaded:time.sleep(1)
            # Airport-major layout lets the browser fetch just one small bucket.
            data=np.stack(values,axis=1).astype('<f4');chunks=[]
            if not np.isfinite(data).any():raise ValueError('No finite airport forecasts')
            for start in range(0,len(airports),CHUNK_SIZE):
                filename=f'{model["id"]}-{cycle:%Y%m%d%H}-airports-{start//CHUNK_SIZE:04d}.bin'
                path=staging/filename;block=data[start:start+CHUNK_SIZE];path.write_bytes(block.tobytes());keep.add(filename)
                chunks.append(dict(filename=filename,sha256=digest(path),start=start,count=len(block)))
            products.append(dict(id=model['id'],name=model['name'],model_run=model['model_run'],
                times=[f['valid_time_utc'] for f in model['frames']],hours=[f['hour'] for f in model['frames']],
                chunks=chunks,fields=['temperature_f','wind10_kt','precipitation_rate_mm_hr'],
                source_urls=[f['source_url'] for f in model['frames']],
                wind_source='NOAA NOMADS UGRD/VGRD at 10 m above ground',native_resolution=model['native_resolution']))
        if not products:raise ValueError('No available model for airport meteograms')
        result=dict(schema_version=1,generated_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
            catalog_filename='catalog.json',catalog_sha256=digest(catalog),catalog_count=len(airports),
            catalog_source=CATALOG_URL,catalog_retrieved_at_utc=catalog_time,chunk_size=CHUNK_SIZE,models=products,
            notes=['Nearest native model grid point, not an observation, TAF, or official aviation forecast.',
                'Precipitation is instantaneous liquid-equivalent rate in mm/hour, not interval accumulation or probability.',
                'Wind is 10 m model sustained speed in knots, not gust speed.',
                'CONUS US airports only. Airport identifiers and locations: OurAirports, public domain.'])
        (staging/'latest.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        for filename in keep-{'latest.json'}:os.replace(staging/filename,output/filename)
        os.replace(staging/'latest.json',output/'latest.json')
        for path in output.glob('*-airports-*.bin'):
            if path.name not in keep:path.unlink()
    LOG.info('Published %d airport models for %d airports',len(products),len(airports))
    return result


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    try:generate()
    except Exception:
        LOG.exception('Airport meteogram generation failed');return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
