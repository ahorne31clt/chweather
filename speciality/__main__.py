"""Headless specialty outlooks: python -m specialty --product daily (or all)."""
import argparse,json,hashlib,logging,os,tempfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
import numpy as np
from shapely import intersects_xy
from sunset.data import session,geography
from weather.sources import get_nc,iso
from .config import PRODUCTS
from .data import NBM,cycles,window,fronts
from .science import solar_altitude,mean_where,index_score,frost_categories,accumulate
from .render import render

ROOT=Path(__file__).resolve().parent.parent
LOG=logging.getLogger('specialty')


def targets(geo):
    regions={};latitudes=[];longitudes=[];offset=0
    for name,bounds,step in [('national',(-125,-66,24,50),.15),('nc',(-84.6,-75,33.5,37.3),.025)]:
        west,east,south,north=bounds;lat=np.arange(south,north+step/2,step);lon=np.arange(west,east+step/2,step)
        xx,yy=np.meshgrid(lon,lat);land=intersects_xy(geo['usa' if name=='national' else 'nc'],xx,yy)
        size=int(land.sum());regions[name]=dict(lat=lat,lon=lon,land=land,start=offset,end=offset+size)
        offset+=size;latitudes.extend(yy[land]);longitudes.extend(xx[land])
    return regions,np.asarray(latitudes),np.asarray(longitudes)


def calculate(kind,reader,a,b,lat,lon):
    hours=list(range(a+3,b+1,3));times=[reader.run+timedelta(hours=h) for h in hours]
    altitude=np.array([solar_altitude(t,lat,lon) for t in times]);meta={};layers={}
    if kind in ('snow','ice'):
        return accumulate([(h-6,h,reader.fetch(h,kind,interval=6)) for h in range(a+6,b+1,6)],a,b),meta,layers
    if kind=='confidence':
        hour=a+12;low=reader.fetch(hour,'temp',percentile=10);high=reader.fetch(hour,'temp',percentile=90)
        if np.any(high[np.isfinite(high)&np.isfinite(low)]<low[np.isfinite(high)&np.isfinite(low)]):raise ValueError('NBM percentiles are not ordered')
        return high-low,{'confidence_valid_at_utc':iso(reader.run+timedelta(hours=hour))},layers
    needed={'daily':['temp'],'outdoor':['temp','rh','wind','gust'],'comfort':['temp','rh','wind'],'stargazing':['cloud','rh','wind'],'frost':['temp','rh','wind','cloud']}[kind]
    fields={name:np.array([reader.fetch(h,name) for h in hours]) for name in needed}
    if kind in ('outdoor','comfort','daily'):
        probability={h:reader.fetch(h,'pop',interval=6) for h in range(a+6,b+1,6)}
        pop=np.array([probability[a+((h-a+5)//6)*6] for h in hours])
    if kind=='daily':
        data=np.max(fields['temp'],axis=0);layers['rain']=np.max(pop,axis=0)
    elif kind in ('outdoor','comfort'):
        data=mean_where(index_score(kind,fields['temp'],fields['rh'],fields['wind'],pop,fields.get('gust')),altitude>5)
    elif kind=='stargazing':
        score=np.clip(100-fields['cloud']-.3*np.maximum(fields['rh']-85,0)-2*np.maximum(fields['wind']-10,0),0,100)
        data=mean_where(score,altitude< -18)
        import astronomy
        time=astronomy.Time.Parse(iso(reader.run+timedelta(hours=a+6)))
        meta['moon']=dict(illuminated_percent=100*astronomy.Illumination(astronomy.Body.Moon,time).phase_fraction,calculated_at_utc=str(time),method='Astronomy Engine 2.1.19; shown separately, not an index correction')
    else:data=frost_categories(fields['temp'],fields['rh'],fields['wind'],fields['cloud'],altitude< -6)
    return data,meta,layers


def run(kind,now=None):
    now=now or datetime.now(timezone.utc);cache=ROOT/'.cache/specialty';cache.mkdir(parents=True,exist_ok=True)
    output=ROOT/'generated'/('specialty-'+kind);output.mkdir(parents=True,exist_ok=True)
    with session() as http:
        usa,countries,states=geography(http,ROOT/'.cache/sunset')
        geo=dict(usa=usa,countries=countries,states=states,nc=get_nc(http,cache))
    regions,lat,lon=targets(geo);errors=[]
    for cycle in cycles(now):
        try:
            a,b=window(now,cycle);reader=NBM(cache,cycle,lat,lon)
            data,details,layers=calculate(kind,reader,a,b,lat,lon)
            if np.isfinite(data).sum()<len(data)*.95:raise ValueError('Outlook contains too many missing land points')
            break
        except Exception as error:
            errors.append(str(error));LOG.warning('%s cycle %s unavailable: %s',kind,cycle,error)
    else:raise RuntimeError('No complete NBM cycle for '+kind+': '+'; '.join(errors))
    spec=PRODUCTS[kind];meta=dict(schema_version=1,id='specialty-'+kind,generated_at_utc=iso(now),model_run=iso(cycle),
        valid_start_utc=iso(cycle+timedelta(hours=a)),valid_end_utc=iso(cycle+timedelta(hours=b)),forecast_valid_date=(cycle+timedelta(hours=a)).date().isoformat(),
        title=spec['title'],kind=spec['kind'],description=spec['description'],method=spec['method'],source='NOAA/NCEP National Blend of Models',source_urls=reader.sources,native_grid_km=2.539703,
        units=spec['unit'],levels=spec['levels'],colors=spec['colors'],sampling='Nearest native point; CONUS 0.15°, NC 0.025°; 3-hourly time samples',products=[],**details)
    front=None
    if kind=='daily':front,meta['fronts']=fronts(cycle+timedelta(hours=a),cycle+timedelta(hours=b))
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        temporary=Path(temporary)
        for name,target in regions.items():
            values=np.full(target['land'].shape,np.nan);values[target['land']]=data[target['start']:target['end']]
            rain=None
            if 'rain' in layers:
                rain=np.full(values.shape,np.nan);rain[target['land']]=layers['rain'][target['start']:target['end']]
            filename=f'{kind}-{name}.png';path=temporary/filename
            render(path,ROOT,kind,name,target['lat'],target['lon'],values,geo,meta,front,rain)
            meta['products'].append(dict(id=f'{kind}-{name}',region=name,image_filename=filename,image_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            LOG.info('Rendered %s %s',kind,name)
        (temporary/'latest.json').write_text(json.dumps(meta,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        for product in meta['products']:os.replace(temporary/product['image_filename'],output/product['image_filename'])
        os.replace(temporary/'latest.json',output/'latest.json')
    return meta


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--product',choices=['all',*PRODUCTS],default='all');args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s');failures=[]
    for kind in PRODUCTS if args.product=='all' else [args.product]:
        try:run(kind)
        except Exception:LOG.exception('%s outlook failed; other products continue',kind);failures.append(kind)
    return 1 if failures else 0


if __name__=='__main__':raise SystemExit(main())
