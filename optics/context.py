"""Independent HRRR cloud refinement and timestamped GOES observations."""
from datetime import datetime,timedelta,timezone
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlparse
import cartopy.crs as ccrs
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from sunset.data import download
from sunset.hrrr import candidate_runs,params_for,read_grib,FILTER


def hrrr_clouds(http,cache,times,lat,lon):
    errors=[];xx,yy=np.meshgrid(lon,lat)
    for run in candidate_runs(times[0]-timedelta(hours=1)):
        leads=[int((t-run).total_seconds()/3600) for t in times]
        if min(leads)<0 or max(leads)>48:continue
        try:
            sampled={};urls=[];identity=None;points=None
            for lead in [leads[-1],*leads[:-1]]:
                path=Path(cache)/f'hrrr-{run:%Y%m%d%H}-f{lead:03d}-clouds.grib2'
                query=params_for(run,lead)
                import requests
                url=requests.Request('GET',FILTER,params=query).prepare().url
                if not path.exists():download(http,FILTER,path,query,maximum=20_000_000)
                grid,fields=read_grib(path,run,lead)
                if identity is None:
                    identity=grid
                    globe=ccrs.Globe(ellipse=None,semimajor_axis=grid['radius'],semiminor_axis=grid['radius'])
                    projection=ccrs.LambertConformal(central_longitude=grid['LoVInDegrees'],central_latitude=grid['LaDInDegrees'],standard_parallels=(grid['Latin1InDegrees'],grid['Latin2InDegrees']),globe=globe)
                    x0,y0=projection.transform_point(grid['longitudeOfFirstGridPointInDegrees'],grid['latitudeOfFirstGridPointInDegrees'],ccrs.PlateCarree())
                    x=x0+np.arange(grid['Ni'])*3000;y=y0+np.arange(grid['Nj'])*3000
                    xy=projection.transform_points(ccrs.PlateCarree(),xx,yy);points=np.column_stack([xy[...,1].ravel(),xy[...,0].ravel()])
                elif grid!=identity:raise ValueError('HRRR cloud grids differ')
                sampled[lead]={k:RegularGridInterpolator((y,x),v,bounds_error=False,fill_value=np.nan)(points).reshape(xx.shape)*(1 if k=='visibility' else 100) for k,v in fields.items()}
                urls.append(url)
            return [sampled[h] for h in leads],dict(status='available',model_run=run.isoformat().replace('+00:00','Z'),native_grid_km=3,sampled_grid_degrees=float(lon[1]-lon[0]),interval_hours=1,source_urls=urls,
                method='Hourly HRRR low/middle/high cloud and visibility replace GFS fields where all four are available. GFS retains upper-air ice/moisture/temperature and precipitation. No satellite observations are extrapolated into the forecast.')
        except Exception as error:errors.append(str(error))
    return None,dict(status='unavailable',reason='; '.join(errors) or 'No extended HRRR run reaches the entire window')


class Images(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='img' and a.get('id','').startswith('F_'):self.urls.append(a.get('src',''))


def satellite(http,output,now):
    records=[];errors=[]
    for platform in ('19','18'):
        for band in ('04','13'):
            page=f'https://www.star.nesdis.noaa.gov/GOES/conus_band.php?sat=G{platform}&band={band}&length=12'
            try:
                response=http.get(page,timeout=(10,30));response.raise_for_status()
                if len(response.content)>500_000:raise ValueError('Oversized satellite index')
                parser=Images();parser.feed(response.text);candidates=[]
                for url in parser.urls:
                    parsed=urlparse(url);match=re.search(r'/(\d{4})(\d{3})(\d{2})(\d{2})_GOES',parsed.path)
                    if parsed.scheme!='https' or parsed.hostname!='cdn.star.nesdis.noaa.gov' or f'/GOES{platform}/ABI/CONUS/' not in parsed.path or f'-{band}-' not in parsed.path or not match:continue
                    y,d,h,m=map(int,match.groups());stamp=datetime(y,1,1,tzinfo=timezone.utc)+timedelta(days=d-1,hours=h,minutes=m)
                    if not -timedelta(minutes=10)<=now-stamp<=timedelta(hours=2):continue
                    candidates.append((stamp,url))
                if not candidates:raise ValueError('No fresh timestamped satellite image')
                stamp,url=max(candidates);name=f'goes-{platform}-{band}.png'
                download(http,url,output/name,maximum=8_000_000)
                from PIL import Image
                with Image.open(output/name) as image:image.convert('RGB').save(output/name,format='PNG',optimize=True)
                records.append(dict(platform='GOES-'+platform,band=band,observed_at_utc=stamp.isoformat().replace('+00:00','Z'),image_filename=name,source_url=url,
                    description='Daytime 1.37 micrometer cirrus reflectance; dark imagery can mean night, not clear sky.' if band=='04' else '10.3 micrometer infrared cloud-top context; not a direct ice-crystal habit measurement.'))
            except Exception as error:errors.append(dict(platform=platform,band=band,reason=str(error)))
    return dict(status='available' if records else 'unavailable',observations=records,failures=errors,
        used_in_forecast_score=False,method='Fresh NOAA imagery for observational comparison only; not assimilated into future ingredient scores.')
