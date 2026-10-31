from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,logging,os,tempfile

from sunset.data import session,geography
from .data import fetch_rtma,fetch_metars,METARS
from .render import render,REGIONS,FIELDS

ROOT=Path(__file__).resolve().parent.parent


def run():
    now=datetime.now(timezone.utc);cache=ROOT/'.cache/analysis';cache.mkdir(parents=True,exist_ok=True)
    output=ROOT/'generated/analysis';output.mkdir(parents=True,exist_ok=True)
    with session() as http:
        run,fields,grid,source=fetch_rtma(http,cache,now)
        geo=geography(http,ROOT/'.cache/sunset')
        stations=fetch_metars(http,cache,datetime.now(timezone.utc),run,geo[0])
    with tempfile.TemporaryDirectory(dir=output) as temp:
        temp=Path(temp);images=[];regions=[]
        for region,(name,extent) in REGIONS.items():
            coordinates=None
            for field,(title,unit,_) in FIELDS.items():
                filename=f'{region}-{field}.png';path=temp/filename
                layout=render(path,ROOT,run,fields,grid,geo,region,field,stations)
                if coordinates is None:coordinates=layout
                images.append(dict(region=region,field=field,image_filename=filename,image_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            regions.append(dict(id=region,label=name,**coordinates))
        stationpath=temp/'stations.json';stationpath.write_text(json.dumps(dict(stations=stations,regions=regions),separators=(',',':'),allow_nan=False),encoding='utf-8')
        times=[s['observation_time'] for s in stations]
        result=dict(schema_version=1,analysis_name='NOAA/NCEP RTMA 2.5 km',analysis_valid_utc=run.isoformat().replace('+00:00','Z'),
            generated_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),native_grid_spacing_m=grid['dx'],
            image_width=2400,image_height=1350,station_count=len(stations),station_time_min_utc=min(times),station_time_max_utc=max(times),
            station_max_analysis_offset_minutes=90,stations_filename='stations.json',stations_sha256=hashlib.sha256(stationpath.read_bytes()).hexdigest(),
            source_url=source,stations_source_url=METARS,regions=[dict(id=id,label=value[0]) for id,value in REGIONS.items()],
            fields=[dict(id=id,label=value[0],unit=value[1]) for id,value in FIELDS.items()],images=images,
            notes=['RTMA is an analysis, not a forecast or raw observation.',
                'METAR observations are independently timestamped, at most two hours old on retrieval and within 90 minutes of RTMA valid time.',
                'Humidity is derived from RTMA temperature and dewpoint using a Magnus approximation, clipped 0–100%.',
                'Station SLP is reported METAR sea-level pressure, never inferred from altimeter setting.'])
        manifest=temp/'latest.json';manifest.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        for path in temp.iterdir():
            if path.name!='latest.json':os.replace(path,output/path.name)
        os.replace(manifest,output/'latest.json')
    print(f'Published RTMA {result["analysis_valid_utc"]}, {len(stations)} METAR stations, {len(images)} maps',flush=True)
    return result


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    try:run()
    except Exception:logging.exception('RTMA/station refresh failed; previous publication retained');raise SystemExit(1)
