"""python -m weather: generate the SPC, national/NC, rain and foliage products."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import hashlib
import logging
import os
import tempfile
import sys

import numpy as np
from shapely import intersects_xy
from sunset.data import session, geography
from .sources import get_spc,get_ndfd,sample_ndfd,get_nc,get_foliage,iso
from .render import render

ROOT=Path(__file__).resolve().parent.parent
LOG=logging.getLogger('weather')
NATIONAL_CITIES=[('Seattle',47.606,-122.332),('Los Angeles',34.052,-118.244),('Denver',39.739,-104.990),
 ('Dallas',32.777,-96.797),('Chicago',41.878,-87.630),('Charlotte',35.227,-80.843),('New York',40.713,-74.006),('Miami',25.762,-80.192)]
NC_CITIES=[('Asheville',35.595,-82.552),('Charlotte',35.227,-80.843),('Boone',36.217,-81.674),
 ('Greensboro',36.073,-79.792),('Raleigh',35.780,-78.638),('Fayetteville',35.053,-78.878),
 ('Wilmington',34.226,-77.945),('Greenville',35.612,-77.366),('Elizabeth City',36.295,-76.251)]


def city_values(cities,temp=None,pop=None):
    result=[]
    for name,lat,lon in cities:
        value=dict(name=name,lat=lat,lon=lon)
        for key,dataset in [('high_f',temp),('pop_percent',pop)]:
            if dataset is not None:
                tree,values,_=dataset
                distance,index=tree.query([lon,lat],distance_upper_bound=.1)
                value[key]=round(float(values[index]),1) if np.isfinite(distance) else None
        result.append(value)
    return result


def run():
    now=datetime.now(timezone.utc);day=now.astimezone(ZoneInfo('America/New_York')).date()
    cache=ROOT/'.cache/weather';cache.mkdir(parents=True,exist_ok=True)
    output=ROOT/'generated/weather';output.mkdir(parents=True,exist_ok=True)
    products=[];failures=[]
    with session() as http, tempfile.TemporaryDirectory(dir=output) as staging:
        staging=Path(staging)
        usa,countries,states=geography(http,ROOT/'.cache/sunset')
        geo=dict(usa=usa,countries=countries,states=states,nc=get_nc(http,cache))
        def publish(product,**kwargs):
            product['generated_at_utc']=iso(now)
            product['image_filename']=product['id']+'.png'
            path=staging/product['image_filename']
            render(path,ROOT,product,geo,**kwargs)
            product['image_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            products.append(product)
            LOG.info('Rendered %s',product['id'])
        def attempt(name,action):
            try:return action()
            except Exception as error:
                failures.append(dict(id=name,error=str(error)))
                LOG.exception("%s failed; successful products will still publish",name)
        for day_number in (1,2,3):
            try:
                records,meta=get_spc(http,cache,day_number,now)
                publish(dict(meta,id=f'spc-day{day_number}',title=f'SPC DAY {day_number} OUTLOOK',
                    subtitle='CONUS / OFFICIAL CATEGORICAL RISK',type='spc',region='national',
                    cities=city_values(NATIONAL_CITIES)),records=records)
            except Exception as error:
                failures.append(dict(id=f"spc-day{day_number}",error=str(error)))
                LOG.exception("SPC Day %s failed; other products continue",day_number)
        def daytime_forecasts():
            high=get_ndfd(http,cache,'maxt',now)
            pop=get_ndfd(http,cache,'pop12',now)
            if (high[2]['valid_start_utc'],high[2]['valid_end_utc']) != (pop[2]['valid_start_utc'],pop[2]['valid_end_utc']):
                raise ValueError('Temperature and precipitation forecast periods do not match')
            for region in ('national','nc'):
                if region=='national':lat=np.arange(24,50.001,.25);lon=np.arange(-125,-65.999,.25)
                else:lat=np.arange(33.5,37.301,.05);lon=np.arange(-84.6,-74.999,.05)
                xx,yy=np.meshgrid(lon,lat)
                mask=intersects_xy(geo['usa' if region=='national' else 'nc'],xx,yy)
                cities=NC_CITIES if region=='nc' else NATIONAL_CITIES
                highs=sample_ndfd(high[0],high[1],lat,lon);pops=sample_ndfd(pop[0],pop[1],lat,lon)
                # The renderer clips to the actual polygon, rather than exposing
                # quarter-degree stair steps along the state/national perimeter.
                if np.isfinite(highs).sum()<100 or np.isfinite(pops).sum()<100:
                    raise ValueError('Not enough valid national/regional forecast points')
                title='CAROLINA' if region=='nc' else 'NATIONAL'
                publish(dict(high[2],id=f'weather-{region}',title=f'{title} WEATHER OUTLOOK',
                    subtitle='NWS DAYTIME HIGHS / MATCHING 12-HOUR PRECIPITATION CHANCE',
                    type='weather',region=region,cities=city_values(cities,high,pop),
                    precipitation_source=pop[2],forecast_valid_date=high[2]['valid_start_utc'][:10]),lat=lat,lon=lon,values=highs)
                publish(dict(pop[2],id=f'rain-{region}',title=f'{title} PRECIPITATION CHANCE',
                    subtitle='NWS NDFD / ONE DAYTIME 12-HOUR INTERVAL / RAIN OR SNOW',
                    type='rain',region=region,cities=city_values(cities,pop=pop),
                    forecast_valid_date=pop[2]['valid_start_utc'][:10]),lat=lat,lon=lon,values=pops)
        attempt("ndfd-daytime",daytime_forecasts)
        def foliage_forecasts():
            foliage,meta=get_foliage(http,cache,day)
            if foliage:
                for region in ('national','nc'):
                    publish(dict(meta,id=f'foliage-{region}',title=('CAROLINA' if region=='nc' else 'NATIONAL')+' FALL COLOR',
                        subtitle='EXPLORE FALL / DATED FOLIAGE-MODEL ESTIMATE',type='foliage',region=region,
                        cities=city_values(NC_CITIES if region=='nc' else NATIONAL_CITIES)),raster=foliage)
            return "available" if foliage else "out_of_season"
        foliage_status=attempt("foliage",foliage_forecasts) or "unavailable"
        if not products:raise RuntimeError("No weather product succeeded; no new manifest published")
        manifest=dict(schema_version=1,generated_at_utc=iso(now),products=products,
            foliage_status=foliage_status,failed_products=failures,status='partial' if failures else 'available')
        text=json.dumps(manifest,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        (staging/'latest.json').write_text(text,encoding='utf-8')
        # Commit successful products together; failed products remain explicitly reported.
        for product in products:os.replace(staging/product['image_filename'],output/product['image_filename'])
        os.replace(staging/'latest.json',output/'latest.json')
    LOG.info('Saved %d real-data products',len(products))
    return manifest


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    try:
        result=run()
        if result.get("failed_products"):
            LOG.error("Partial weather batch saved; failed products remain reported as failures")
            return 1
    except Exception:
        LOG.exception('Weather products failed; no illustrative data substituted')
        return 1
    return 0


if __name__=='__main__':sys.exit(main())
