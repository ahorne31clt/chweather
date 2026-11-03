"""One headless command: python -m optics. No credentials required."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import hashlib,json,logging,os,tempfile,time
import numpy as np
from shapely import intersects_xy
from sunset.data import session,geography
from .data import cycles,fetch
from .science import score,PHENOMENA
from .render import render
from .context import hrrr_clouds,satellite

ROOT=Path(__file__).resolve().parents[1]
LOG=logging.getLogger('optics')
SOURCES=['https://www.weather.gov/arx/why_halos_sundogs_pillars','https://www.weather.gov/fgz/Rainbow',
 'https://my.weather.gov.hk/en/education/weather/clouds/00499-circumhorizontal-arc.html',
 'https://cloudatlas.wmo.int/en/circumzenithal-arc.html','https://www.faa.gov/contrails','https://py.contrails.org/api/pycontrails.models.sac.html','https://doi.org/10.1256/qj.04.94']


def iso(t):return t.isoformat(timespec='seconds').replace('+00:00','Z')


def run(now=None):
    now=now or datetime.now(timezone.utc);start=now.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)
    times=[start+timedelta(hours=h) for h in range(24)]
    cache=ROOT/'.cache/optics';cache.mkdir(parents=True,exist_ok=True)
    for old in cache.glob('*.grib2'):
        if time.time()-old.stat().st_mtime>4*86400:old.unlink()
    errors=[]
    with session() as http:
        for run_time in cycles(now):
            try:
                a=int((times[0]-run_time).total_seconds()/3600);b=int((times[-1]-run_time).total_seconds()/3600)
                hours=list(range(a//3*3,(b+2)//3*3+1,3));frames={};urls=[];axes=None
                for hour in hours:
                    LOG.info('Fetching GFS optics %s f%03d',iso(run_time),hour)
                    fields,new_axes,url=fetch(http,cache,run_time,hour)
                    if axes is not None and any(not np.array_equal(x,y) for x,y in zip(axes,new_axes)):raise ValueError('Optics forecast grids changed between hours')
                    axes=new_axes;frames[hour]=fields;urls.append(url)
                break
            except Exception as error:errors.append(str(error));LOG.warning('Optics cycle failed: %s',error)
        else:raise RuntimeError('No complete current GFS optics run: '+'; '.join(errors))
        geo=geography(http,ROOT/'.cache/sunset')
    lat,lon=axes;xx,yy=np.meshgrid(lon,lat);land=intersects_xy(geo[0],xx,yy)
    cities=json.loads((ROOT/'sunset/cities.json').read_text(encoding='utf-8'))
    city_indices=[(int(np.argmin(abs(lat-c['lat']))),int(np.argmin(abs(lon-c['lon'])))) for c in cities]
    with session() as http:
        refinements,hrrr_meta=hrrr_clouds(http,cache,times,lat,lon)
    LOG.info('HRRR cloud refinement: %s',hrrr_meta['status'])
    sampled_inputs=[]
    baseline_scores={k:[] for k in PHENOMENA};coverage=[]
    cubes={k:[] for k in PHENOMENA};altitudes=[]
    for valid in times:
        hour=int((valid-run_time).total_seconds()/3600);lower=hour//3*3;upper=min(lower+3,hours[-1]);fraction=(hour-lower)/3
        fields={k:(1-fraction)*frames[lower][k]+fraction*frames[upper][k] for k in frames[lower]}
        baseline,_=score(fields,valid,lat,lon)
        for key,value in baseline.items():baseline_scores[key].append([int(round(value[i,j])) for i,j in city_indices])
        if refinements is not None:
            refined=refinements[len(altitudes)];usable=np.logical_and.reduce([np.isfinite(v) for v in refined.values()])
            coverage.append(float(usable[land].mean()))
            fields.update({k:np.where(usable,v,fields[k]) for k,v in refined.items()})
        from .contrails import diagnose
        contrail=diagnose(fields)
        fields.update(contrail_pressure_hpa=contrail['pressure_hpa'],contrail_rhi_percent=contrail['rhi']*100,
                      contrail_temperature_c=contrail['temperature_c'])
        sampled_inputs.append([{k:round(float(v[i,j]),8 if k.startswith(('ice','q')) or k=='rate' else 2) for k,v in fields.items()} for i,j in city_indices])
        scores,altitude=score(fields,valid,lat,lon);altitudes.append(altitude)
        for k,value in scores.items():cubes[k].append(value)
    cubes={k:np.stack(v) for k,v in cubes.items()};altitudes=np.stack(altitudes)
    conus=land&(xx>=-125)&(xx<=-66)&(yy>=24)&(yy<=50)
    if any(np.isfinite(v[:,conus]).mean()<.99 for v in cubes.values()):raise ValueError('Incomplete optics viewing-ray coverage')
    if coverage:hrrr_meta['land_coverage_fraction']=min(coverage)
    meta=dict(schema_version=2,model='HRRR cloud refinement + GFS upper air/rain' if refinements is not None else 'NOAA/NCEP GFS 0.25 degree',hrrr=hrrr_meta,model_run=iso(run_time),generated_at_utc=iso(datetime.now(timezone.utc)),
      forecast_valid_date=start.date().isoformat(),valid_start_utc=iso(times[0]),valid_end_utc=iso(times[-1]+timedelta(hours=1)),
      forecast_times_utc=[iso(t) for t in times],native_grid_degrees=.25,input_time_interval_hours=3,geometry_interval_hours=1,
      score_is_probability=False,algorithm_version='optics-ingredients-v3',source_urls=urls+hrrr_meta.get('source_urls',[]),research_sources=SOURCES,
      contrail_method=dict(pressure_levels_hpa=[200,250,300,350],humidity='Ice-relative humidity derived from specific humidity, pressure and Murphy-Koop ice saturation pressure; no inference from ambiguous model RH.',
          formation='Schmidt-Appleman mixing-line test against liquid saturation; generic Jet-A assumptions.',engine_efficiency=.35,water_emission_index_kg_per_kg=1.25,heat_capacity_j_per_kg_k=1004,fuel_heat_j_per_kg=43e6,
          categories={'0':'No qualifying sampled formation environment','1':'Formation possible; ambient ice supersaturation absent','2':'Formation criterion met and ice-relative humidity at least 100%'},
          conditional_on_aircraft=True,uses_airport_proximity=False,uses_flight_traffic=False,
          limitations='Four coarse pressure surfaces can miss thin supersaturated layers. No humidity-bias correction, engine-specific performance, wake survival, cloud lifetime, advection, crystal habit or halo probability is predicted. Nighttime formation is allowed.'),
      pressure_levels_hpa=[300,400,500],products=[],locations_filename='locations.json',
      limitations=['Unvalidated ingredient index; not an occurrence probability or official NWS forecast.',
       'High cloud fraction is not optical depth. Crystal habit, size, orientation, turbulence and 3-D radiative transfer are unresolved.',
       'RH uses the published model convention; it is not a calculation of ice supersaturation.',
       'The 22-degree halo and upper tangent arc share the same ingredient score: unresolved crystal orientation distinguishes them.',
       'Rain is sampled 10-40 km in an antisolar sector; sunward cloud blocking uses a simplified 40 km horizontal ray, not ray tracing.',
       'Three-hourly cloud/precipitation inputs are linearly interpolated hourly. Sub-hour showers, terrain, buildings and exact cloud location can dominate.',
       'Index zero can mean unsuitable geometry. Circumhorizontal arcs are seasonally impossible at many northern locations.',
       'Do not look directly at the Sun. Observe with the Sun safely blocked; do not use binoculars or telescopes.'])
    locations=[]
    for city_number,city in enumerate(cities):
        i=int(np.argmin(abs(lat-city['lat'])));j=int(np.argmin(abs(lon-city['lon'])))
        if not conus[i,j]:continue
        locations.append(dict(name=city['name'],lat=city['lat'],lon=city['lon'],solar_elevation_degrees=np.round(altitudes[:,i,j],1).tolist(),
            hourly_ingredients=[row[city_number] for row in sampled_inputs],
            gfs_scores={k:[row[city_number] for row in values] for k,values in baseline_scores.items()},
            scores={k:np.rint(v[:,i,j]).astype(int).tolist() for k,v in cubes.items()}))
    output=ROOT/'generated/optics';output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as directory:
        temp=Path(directory)
        for key,cube in cubes.items():
            values=np.max(cube,axis=0);values=np.where(land,values,np.nan)
            for region in ('national','nc'):
                name=f'{key}-{region}.png';render(temp/name,ROOT,key,region,lat,lon,values,geo,meta)
                meta['products'].append(dict(id=key,region=region,title=PHENOMENA[key][0],description=PHENOMENA[key][1],image_filename=name,image_sha256=hashlib.sha256((temp/name).read_bytes()).hexdigest()))
        (temp/'locations.json').write_text(json.dumps(dict(times=meta['forecast_times_utc'],locations=locations),allow_nan=False,separators=(',',':')),encoding='utf-8')
        with session() as http:meta['satellite']=satellite(http,temp,datetime.now(timezone.utc))
        (temp/'latest.json').write_text(json.dumps(meta,allow_nan=False,indent=2)+'\n',encoding='utf-8')
        for path in temp.iterdir():
            if path.name!='latest.json':os.replace(path,output/path.name)
        os.replace(temp/'latest.json',output/'latest.json')
    LOG.info('Published %s solar-optics maps',len(meta['products']))
    return meta


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    try:run()
    except Exception:LOG.exception('Optics failed; no invented data substituted');return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
