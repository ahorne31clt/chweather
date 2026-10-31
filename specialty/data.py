from datetime import datetime,timedelta,timezone
from pathlib import Path
import hashlib,re,json
import eccodes as ec
import numpy as np
import cartopy.crs as ccrs
from ensembles.data import index,choose,decode,http
from models.render import projection_for,native_axes
from scipy.interpolate import RegularGridInterpolator


def convert_field(name,values):
    if name=='temp':return (values-273.15)*1.8+32
    if name in ('wind','gust'):return values*2.236936292
    if name=='snow':return values/.0254
    if name=='ice':return values/25.4
    return values


def normalize_scan(values,alternating,j_consecutive=0):
    """Return ordinary west/east rows from GRIB's alternating-row storage."""
    if j_consecutive:raise ValueError('Column-major NBM scanning is not supported')
    if alternating:
        values=values.copy();values[1::2]=values[1::2,::-1].copy()
    return values


def cycles(now):
    ready=now-timedelta(hours=4)
    first=ready.replace(hour=ready.hour//12*12,minute=0,second=0,microsecond=0)
    return [first-timedelta(hours=12*i) for i in range(3)]


def window(now,run):
    start=now.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)
    a=int((start-run).total_seconds()/3600);return a,a+24


class NBM:
    def __init__(self,cache,run,lat,lon):
        self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True);self.run=run
        self.lat=lat;self.lon=lon;self.grid_id=None;self.points=None;self.sources=[]

    def fetch(self,hour,name,interval=None,percentile=None):
        names={'temp':('TMP','2 m above ground',(0,0,0)),'rh':('RH','2 m above ground',(0,1,1)),
          'wind':('WIND','10 m above ground',(0,2,1)),'gust':('GUST','10 m above ground',(0,2,22)),
          'cloud':('TCDC','surface',(0,6,1)),'pop':('APCP','surface',(0,1,8)),
          'snow':('ASNOW','surface',(0,1,29)),'ice':('FICEAC','surface',(0,1,228))}
        variable,level,parameter=names[name];kind='qmd' if percentile is not None else 'core'
        url=f'https://noaa-nbm-grib2-pds.s3.amazonaws.com/blend.{self.run:%Y%m%d}/{self.run:%H}/{kind}/blend.t{self.run:%H}z.{kind}.f{hour:03d}.co.grib2'
        prefix=self.cache/f'{self.run:%Y%m%d%H}-{kind}-{hour:03d}'
        rows=index(url,str(prefix)+'.idx')
        timing=f'{hour-interval}-{hour} hour acc fcst' if interval else f'{hour} hour fcst'
        tail=f':{variable}:{level}:{timing}:'
        if name=='pop':tail+='prob >0.254:prob fcst 255/255'
        if percentile is not None:tail+=f'{percentile}% level'
        row=choose(rows,lambda line:line.endswith(tail))
        path=Path(str(prefix)+f'-{name}-{interval or 0}-{percentile if percentile is not None else "det"}.grib2')
        if not path.is_file():
            a,b=row['offset'],row['end']
            if b is None or b-a+1>12_000_000:raise ValueError('NBM record exceeds bounded download')
            with http().get(url,headers={'Range':f'bytes={a}-{b}'},timeout=(10,60),stream=True) as response:
                response.raise_for_status()
                if response.status_code!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {a}-{b}/'):raise ValueError('NBM byte range was not honored')
                payload=bytearray()
                for chunk in response.iter_content(65536):
                    payload.extend(chunk)
                    if len(payload)>b-a+1:raise ValueError('Oversized NBM record')
            if len(payload)!=b-a+1:raise ValueError('Incomplete NBM record')
            path.write_bytes(payload)
        payload=path.read_bytes();g=ec.codes_new_from_message(payload)
        try:
            alternating=ec.codes_get(g,'alternativeRowScanning');j_consecutive=ec.codes_get(g,'jPointsAreConsecutive')
            actual=tuple(ec.codes_get(g,k) for k in ['discipline','parameterCategory','parameterNumber'])
            if actual!=parameter or ec.codes_get(g,'typeOfLevel')!=('heightAboveGround' if 'above ground' in level else 'surface'):raise ValueError('NBM parameter or level differs from selection')
            if 'above ground' in level and ec.codes_get(g,'level')!=int(level.split()[0]):raise ValueError('NBM vertical level mismatch')
            if percentile is not None and ec.codes_get(g,'percentileValue')!=percentile:raise ValueError('NBM percentile differs from selection')
        finally:ec.codes_release(g)
        values,grid,attrs=decode(payload,self.run,hour)
        values=normalize_scan(values,alternating,j_consecutive)
        if interval and (attrs['startStep'],attrs['endStep'],attrs['stepType'])!=(hour-interval,hour,'accum'):raise ValueError('NBM accumulation interval differs')
        if not interval and attrs['stepType']!='instant':raise ValueError('Expected an instantaneous NBM field')
        if name=='pop' and (attrs.get('probabilityType')!=1 or attrs.get('scaledValueOfUpperLimit')*10**(-attrs.get('scaleFactorOfUpperLimit'))!=.254):raise ValueError('Unexpected precipitation threshold')
        if self.grid_id is None:
            self.grid_id=grid['id'];projection=projection_for(grid);x,y=native_axes(grid,projection);self.axes=y,x
            xy=projection.transform_points(ccrs.PlateCarree(),self.lon,self.lat);self.points=np.column_stack([xy[:,1],xy[:,0]])
        elif self.grid_id!=grid['id']:raise ValueError('NBM grids differ within the outlook')
        sampled=RegularGridInterpolator(self.axes,values,method='nearest',bounds_error=False,fill_value=np.nan)(self.points)
        finite=sampled[np.isfinite(sampled)]
        if len(finite)<len(sampled)*.8:raise ValueError('Insufficient NBM coverage')
        if name in ('rh','cloud','pop') and (finite.min()<0 or finite.max()>100):raise ValueError('Invalid percentage field')
        if name=='temp' and (finite.min()<170 or finite.max()>350):raise ValueError('Invalid temperature field')
        if name in ('snow','ice','wind','gust') and finite.min()<0:raise ValueError('Negative physical field')
        if url not in self.sources:self.sources.append(url)
        expected_units={'temp':'K','rh':'%','cloud':'%','wind':'m s**-1','gust':'m s**-1'}
        if name in expected_units and attrs['units']!=expected_units[name]:raise ValueError('Unexpected NBM physical units')
        return convert_field(name,sampled)


def parse_front_time(value):
    match=re.fullmatch(r'(\d{1,2})(?::(\d{2}))?(am|pm) (EDT|EST|UTC) (\w{3} \w{3} \d{2} \d{4})',value.strip(),re.I)
    if not match:raise ValueError('Unrecognized WPC front valid time')
    hour=int(match[1])%12+(12 if match[3].lower()=='pm' else 0)
    offset={'EDT':-4,'EST':-5,'UTC':0}[match[4].upper()]
    day=datetime.strptime(match[5],'%a %b %d %Y')
    return day.replace(hour=hour,minute=int(match[2] or 0),tzinfo=timezone(timedelta(hours=offset))).astimezone(timezone.utc)


def fronts(start,end):
    root='https://www.wpc.ncep.noaa.gov/NationalForecastChart/'
    r=http().get(root+'map.php',timeout=30);r.raise_for_status()
    labels=re.findall(r'<center>Weather Valid .*?<br>\s*Fronts Valid (.*?)\s*<br>Issued\s*(.*?)</center>',r.text,re.S)
    if len(labels)!=3:raise ValueError('WPC forecast valid labels missing')
    candidates=[(parse_front_time(v),i,v,issue) for i,(v,issue) in enumerate(labels)]
    target=start+(end-start)/2
    valid,i,label,issued=min(candidates,key=lambda x:(abs((x[0]-target).total_seconds()),-x[0].timestamp()))
    if not start-timedelta(hours=12)<=valid<=end+timedelta(hours=12):raise ValueError('WPC fronts do not cover this forecast period')
    url=root+'mapdata/fronts'+['92f','96f','99f'][i]+'.js';response=http().get(url,timeout=30);response.raise_for_status()
    result={}
    for name in ['TROF','COLD','WARM','STNRY','OCFNT','LOWS','HIGHS']:
        match=re.search(r'\b'+name+r'\.push\((\[.*?\])\);',response.text,re.S)
        if not match:raise ValueError('Incomplete WPC front layer')
        data=json.loads(match[1]);result[name]=data
        points=data if name in ('LOWS','HIGHS') else [p for line in data for p in line]
        if any(len(p)!=2 or not -90<=p[0]<=90 or not -180<=p[1]<=180 for p in points):raise ValueError('Invalid WPC coordinates')
    return result,dict(source_url=url,valid_at_utc=valid.isoformat().replace('+00:00','Z'),publisher_valid_label=label,publisher_issue_label=issued.strip(),metadata_url=root+'map.php')
