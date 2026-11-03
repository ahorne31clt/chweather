"""Fetch, calculate, and render seasonal guidance: python -m seasonal."""
from datetime import datetime,timezone,date
from pathlib import Path
import argparse,hashlib,json,logging,os,tempfile
import numpy as np
from scipy.spatial import cKDTree
from scipy.interpolate import LinearNDInterpolator
from scipy.ndimage import gaussian_filter
from shapely import intersects_xy
from sunset.data import session,geography
from .data import latest_cycles,model_source,probabilities,observations,dense_observations,atmosphere,historical_models,snowfall_normals,additional_indices,enso_forecast
from .blend import calculate as calculate_blend,MODELS
from .science import add_month,months,season_name,seasonal_anomaly,probability_fields,choose_analogs,station_statistics
from .render import render

ROOT=Path(__file__).resolve().parent.parent
LOG=logging.getLogger('seasonal')
LABELS={'blend':'CH Weather Blend / experimental v3','nmme':'NMME','cfs':'CFSv2 Monthly','cansips':'CanSIPS (CanESM5 + GEM5.2-NEMO)','analogs':'ENSO historical analogs'}


def analog_grid(stations,metric,lat,lon,return_support=False):
    xx,yy=np.meshgrid(lon,lat)
    xy=np.array([[s['lon']*.8,s['lat']] for s in stations]);points=np.column_stack([xx.ravel()*.8,yy.ravel()])
    if len(xy)<8:raise ValueError('Fewer than eight usable climate stations')
    values=np.array([s[metric] for s in stations],dtype=float)
    grid=LinearNDInterpolator(xy,values)(points)
    outside=~np.isfinite(grid)
    distance,neighbor=cKDTree(xy).query(points,k=min(6,len(stations)))
    weight=1/np.maximum(distance,.02)**2
    fill=np.sum(values[neighbor]*weight,axis=1)/weight.sum(axis=1)
    grid=np.where(outside,fill,grid).reshape(xx.shape)
    grid=gaussian_filter(grid,sigma=5.5,mode='nearest')
    grid=np.clip(grid,np.min(values),np.max(values))
    if metric in ('above','below','near'):grid=np.clip(grid,0,100)
    if metric in ('amount','normal','expected'):grid=np.maximum(0,grid)
    support=(outside|(distance[:,0]*111>180)).reshape(xx.shape)
    return (grid,support) if return_support else grid


def run(now=None):
    now=now or datetime.now(timezone.utc)
    cache=ROOT/'.cache/seasonal';cache.mkdir(parents=True,exist_ok=True)
    output=ROOT/'generated/seasonal';output.mkdir(parents=True,exist_ok=True)
    import time
    for old in cache.glob('*.data'):
        if time.time()-old.stat().st_mtime>100*86400:old.unlink()
    with session() as http:
        errors=[];selected=None
        for cycle in latest_cycles(http,cache,now):
            try:
                data={};urls=set()
                for model in ['NMME',*MODELS]:
                    for variable in ['temperature','precipitation']:
                        d,url=model_source(http,cache,cycle,model,variable);data[model,variable]=d;urls.add(url)
                prob={}
                for variable in ['temperature','precipitation']:
                    d,url=probabilities(http,cache,cycle,variable);prob[variable]=d;urls.add(url)
                selected=cycle;break
            except Exception as error:errors.append(str(error));LOG.warning('Seasonal cycle %s unavailable: %s',cycle,error)
        if selected is None:raise RuntimeError('No complete recent seasonal initialization: '+'; '.join(errors))
        stations,oni,observation_meta=observations(http,cache,now)
        latest,analogs,phase=choose_analogs(oni,now)
        stations,dense_meta=dense_observations(http,cache,now,stations)
        atmospheric_indices,index_meta=atmosphere(http,cache,now)
        extra_indices,extra_meta=additional_indices(http,cache,now)
        atmospheric_indices.update(extra_indices);index_meta.update(extra_meta)
        history,history_meta=historical_models(http,cache,(int(selected[:4]),int(selected[4:6])),now)
        atmospheric_indices['model_enso']={}
        for year in [*history,int(selected[:4])]:
            try:atmospheric_indices['model_enso'][year]=enso_forecast(http,cache,f'{year}{selected[4:6]}0800')
            except Exception as error:LOG.warning('Issued ENSO forecast unavailable for %s: %s',year,error)
        normal_stations,snow_normal_meta=snowfall_normals(http,cache)
        geo=geography(http,ROOT/'.cache/sunset')
    init=(int(selected[:4]),int(selected[4:6]));starts=[add_month(*init,i) for i in range(1,6)]
    starts=[s for s in starts if s>=(now.year,now.month)]
    if not starts:raise ValueError('No unexpired forecast seasons')
    lat=data['NMME','temperature']['lat'];lon=data['NMME','temperature']['lon']
    xx,yy=np.meshgrid(lon,lat);land=intersects_xy(geo[0],xx,yy)
    fine_lat=np.arange(23,51.001,.2);fine_lon=np.arange(-127,-64.999,.2)
    products=[];windows=[];blend_metadata=[]
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        temp=Path(temporary)
        def save(model,variable,metric,start,values,*,points=None,source_urls=None,axes=None,support=None,duration_months=3,period_id=None):
            suffix='-full' if duration_months==6 else ''
            key=f'{model}-{variable}-{metric}-{start[0]}{start[1]:02d}'+suffix
            image=temp/(key+'.png')
            historical=model=='analogs'
            if model not in ('analogs','blend') and np.isfinite(values[land]).mean()<.9:
                raise ValueError('Seasonal model coverage below 90 percent of CONUS land points')
            measure=('total accumulation' if metric=='total' else 'expected seasonal range' if metric=='amount' else 'anomaly' if metric=='anomaly' else 'experimental chance '+metric+' average' if model=='blend' else 'historical frequency '+metric+' average' if historical else metric+'-normal probability')
            units=('Temperature departure (F)' if variable=='temperature' else variable.title()+' departure (inches)') if metric=='anomaly' else ('Total snowfall central estimate (inches)' if metric=='total' else 'Seasonal snowfall band (inches)' if metric=='amount' else 'Experimental distribution fraction (%)' if model=='blend' else 'Historical analog seasons (%)' if historical else 'Forecast tercile probability (%)')
            meta=dict(id=key,model=model,model_label=LABELS[model],variable=variable,metric=metric,
                season_start=f'{start[0]}-{start[1]:02d}-01',season_end=f'{add_month(*start,duration_months)[0]}-{add_month(*start,duration_months)[1]:02d}-01',
                period_id=period_id or f'{start[0]}-{start[1]:02d}-01',duration_months=duration_months,
                season_label=season_name(start,duration_months),initialization_month=f'{init[0]}-{init[1]:02d}',
                title='Total seasonal snowfall' if metric=='total' else variable.title()+' / '+measure,units_label=units,
                footer=('CH Weather research blend / broad seasonal guidance, not storm totals / probabilities and snow ranges are experimental.' if model=='blend' else 'Historical sample, not calibrated forecast odds. 1991-2020 station normals; regional interpolation with variable observational support.' if historical else 'NOAA CPC NMME data / model-relative anomalies and published adjusted tercile probabilities / not the official CPC outlook.'),
                kind='Experimental CH Weather statistical/dynamical blend' if model=='blend' else 'Historical ENSO analog composite' if historical else 'Seasonal model guidance',source_urls=sorted(source_urls or urls))
            plot_lat,plot_lon=axes if axes is not None else (lat,lon)
            if support is not None:
                gx,gy=np.meshgrid(plot_lon,plot_lat);inside=intersects_xy(geo[0],gx,gy)
                meta['limited_observation_support_land_percent']=round(float(np.asarray(support)[inside].mean()*100),1)
            render(image,ROOT,plot_lat,plot_lon,values,geo,meta,points,support)
            filename=(f'{model}-{variable}-{start[0]}{start[1]:02d}'+suffix if points else key)+'-values.json'
            payload=dict(stations=points or [],raster_values_included=not bool(points))
            if not points:payload.update(lat=lat.tolist(),lon=lon.tolist(),values=np.where(np.isfinite(values),np.round(values,2),None).tolist())
            (temp/filename).write_text(json.dumps(payload,allow_nan=False,separators=(',',':')),encoding='utf-8')
            products.append(dict(meta,image_filename=image.name,values_filename=filename,image_sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
        for start in starts:
            LOG.info('Generating seasonal window %s',season_name(start));windows.append(dict(start=f'{start[0]}-{start[1]:02d}-01',label=season_name(start)))
            for variable in ['temperature','precipitation']:
                for name,models in [('nmme',['NMME']),('cfs',['CFSv2']),('cansips',['CanESM5','GEM5.2_NEMO'])]:
                    all_values=[]
                    for model in models:
                        d=data[model,variable]
                        indices=[d['dates'].index(m) for m in months(start)]
                        all_values.append(d['values']['fcst'][indices])
                    raw=np.mean(all_values,axis=0)
                    values=seasonal_anomaly(raw,start,variable)
                    save(name,variable,'anomaly',start,values)
                d=prob[variable];index=d['dates'].index(start)
                arrays=probability_fields([d['values'][key][index] for key in ['prob_above','prob_norm','prob_below']])
                for metric,values in zip(['above','near','below'],arrays):save('nmme',variable,metric,start,values)
            normal_points=[dict(lat=p['lat'],lon=p['lon'],normal_log=float(np.log1p(sum(p['months'][m] for _,m in months(start))))) for p in normal_stations if all(m in p['months'] for _,m in months(start))]
            if len(normal_points)<2000:raise ValueError('Incomplete seasonal snowfall normal surface')
            normal_log=analog_grid(normal_points,'normal_log',fine_lat,fine_lon)
            snow_baseline=np.maximum(0,np.expm1(normal_log))
            analog_starts=[(r['year']+start[0]-latest['year'],start[1]) for r in analogs]
            for variable in ['temperature','precipitation','snowfall']:
                points=[]
                for station in stations:
                    stats=station_statistics(station['series'],start,analog_starts,variable,include_low_snow=True)
                    if stats is not None:points.append(dict(id=station['id'],name=station['name'],lat=station['lat'],lon=station['lon'],**stats))
                for metric in ['anomaly','above','below']:
                    grid,support=analog_grid(points,metric,fine_lat,fine_lon,True)
                    if variable=='snowfall':
                        if metric=='anomaly':
                            ratio_points=[dict(p,snow_log_factor=float(np.log((max(0,p['normal']+p['anomaly'])+.25)/(p['normal']+.25)))) for p in points]
                            ratio=analog_grid(ratio_points,'snow_log_factor',fine_lat,fine_lon)
                            expected=np.maximum(0,(snow_baseline+.25)*np.exp(ratio)-.25)
                            expected=np.where(snow_baseline<=.01,0,expected)
                            grid=expected-snow_baseline
                        else:grid=np.where(snow_baseline<=.01,0,grid)
                    save('analogs',variable,metric,start,grid,points=points,axes=(fine_lat,fine_lon),support=support,
                         source_urls=[observation_meta['oni_url'],observation_meta['observations_url'],snow_normal_meta['source_url']])
            LOG.info('Fitting CH Weather Blend for %s',season_name(start))
            blend_points,details=calculate_blend(stations,start,init,data,history,oni,atmospheric_indices)
            blend_metadata.append(dict(season_start=f'{start[0]}-{start[1]:02d}-01',**details))
            for variable,points in blend_points.items():
                for metric in ['anomaly','above','below']+(['amount'] if variable=='snowfall' else []):
                    grid,support=analog_grid(points,metric,fine_lat,fine_lon,True)
                    if variable=='snowfall':
                        if metric in ('anomaly','amount'):
                            ratio_points=[dict(p,snow_log_factor=float(np.log((p['expected']+.25)/(p['normal']+.25)))) for p in points]
                            ratio=analog_grid(ratio_points,'snow_log_factor',fine_lat,fine_lon)
                            expected=np.maximum(0,(snow_baseline+.25)*np.exp(ratio)-.25)
                            expected=np.where(snow_baseline<=.01,0,expected)
                            grid=expected-snow_baseline if metric=='anomaly' else expected
                        else:grid=np.where(snow_baseline<=.01,0,grid)
                    save('blend',variable,metric,start,grid,points=points,axes=(fine_lat,fine_lon),support=support,
                        source_urls=list(urls)+[snow_normal_meta['source_url']]+[observation_meta['oni_url'],observation_meta['observations_url']]+[m['source_url'] for m in index_meta.values() if 'source_url' in m])
        # One six-month distribution, never a sum of overlapping seasons.
        snow_year=now.year if now.month>=7 else now.year-1
        full_start=(snow_year,11);period_id=f'snow-season-{snow_year}'
        full_months=months(full_start,6)
        reachable=all(m in data['NMME','temperature']['dates'] or m<init for m in full_months)
        if reachable and (now.year,now.month)<add_month(*full_start,6):
            LOG.info('Generating full November-April snow season %s',snow_year)
            full_points,details=calculate_blend(stations,full_start,init,data,history,oni,atmospheric_indices,duration_months=6)
            windows.append(dict(id=period_id,start=f'{snow_year}-11-01',duration_months=6,label=f'FULL SNOW SEASON / {season_name(full_start,6)}'))
            blend_metadata.append(dict(period_id=period_id,season_start=f'{snow_year}-11-01',duration_months=6,**details))
            points=full_points['snowfall']
            normal_points=[dict(lat=p['lat'],lon=p['lon'],normal_log=float(np.log1p(sum(p['months'][m] for _,m in full_months)))) for p in normal_stations if all(m in p['months'] for _,m in full_months)]
            if len(normal_points)<2000:raise ValueError('Full snow-season normal coverage is incomplete')
            baseline=np.maximum(0,np.expm1(analog_grid(normal_points,'normal_log',fine_lat,fine_lon)))
            ratio_points=[dict(p,snow_log_factor=float(np.log((p['expected']+.25)/(p['normal']+.25)))) for p in points]
            ratio,support=analog_grid(ratio_points,'snow_log_factor',fine_lat,fine_lon,True)
            expected=np.maximum(0,(baseline+.25)*np.exp(ratio)-.25)
            expected=np.where(baseline<=.01,0,expected)
            for metric in ['total','anomaly','above','below','amount']:
                grid=expected if metric in ('total','amount') else expected-baseline if metric=='anomaly' else np.where(baseline<=.01,0,analog_grid(points,metric,fine_lat,fine_lon))
                save('blend','snowfall',metric,full_start,grid,points=points,axes=(fine_lat,fine_lon),support=support,
                     duration_months=6,period_id=period_id,
                     source_urls=list(urls)+[snow_normal_meta['source_url'],observation_meta['oni_url'],observation_meta['observations_url']]+[m['source_url'] for m in index_meta.values() if 'source_url' in m])
        result=dict(schema_version=3,generated_at_utc=now.isoformat(timespec='seconds').replace('+00:00','Z'),
            model_run=f'{init[0]}-{init[1]:02d}',status='ready',windows=windows,products=products,
            analog_selection=dict(index='ONI',latest_observed=latest,phase=phase,selected=analogs,
                method='Ten nearest same-calendar-season ONI values in the same phase; one per historical episode with at least five consecutive threshold seasons. Neutral years selected individually. No future seasonal observations used for selection.'),
            external_guidance=dict(status='not_connected',reason='Additional C3S centers require credentials, accepted data terms, matching hindcasts and independent verification before blend admission.'),
            observations=dict(observation_meta,dense_network=dense_meta,snow_normals=snow_normal_meta),atmosphere=index_meta,blend=blend_metadata,development_archive=history_meta,normal_period='1991-2020',native_grid_degrees=1,display_grid_degrees=.2,regional_smoothing_sigma_km_approx=120,
            methods_url='https://www.cpc.ncep.noaa.gov/products/NMME/data.html',
            notes=['NMME already includes CFSv2 and CanSIPS components. They are comparisons, never added again to NMME.',
                'CanSIPS comparison is an equal mean of the published CanESM5 and GEM5.2-NEMO anomaly means.',
                'Temperature seasonal anomalies are day-weighted and converted from K departures to F departures; precipitation rate departures are integrated by calendar days and converted to inches.',
                'Probabilities are CPC published adjusted seasonal NMME terciles. Above/below terciles differ from above/below the arithmetic average.',
                'Analog frequencies compare historical seasonal values with each city series 1991-2020 arithmetic average; these are not calibrated forecast probabilities.',
                'CH Weather snow guidance conditions observed historical snowfall on the blended temperature/precipitation pattern and observed state; no snow-ratio conversion is used. Conditional strength is selected by earlier-year snow CRPS; limited operational-archive verification is published with each window.',
                'Station composites require complete months and at least 24 normal years. Pure ENSO composites require eight analogs. Low-snow climates are retained, including measured zeros.',
                'Station contours use non-overshooting linear interpolation with broad regional smoothing and flagged edge extrapolation on a 0.2 degree display grid; support metadata identifies extrapolation or limited nearby observations. Display spacing is not effective forecast resolution; mountain and local effects remain unresolved.',
                'CH Weather Blend combines the six individual NMME components once with an observed-state statistical stream. NMME is not added as a seventh model. Nested forward-year verification is published, with model-version and fixed-normal limitations.'])
        (temp/'latest.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        for path in temp.iterdir():
            if path.name!='latest.json':os.replace(path,output/path.name)
        os.replace(temp/'latest.json',output/'latest.json')
    LOG.info('Published %s seasonal maps for %s',len(products),selected)
    return result


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    try:run()
    except Exception:LOG.exception('Seasonal generation failed; no invented data substituted');return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
