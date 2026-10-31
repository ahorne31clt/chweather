from datetime import datetime,timezone,timedelta
from pathlib import Path
import hashlib,json,logging,os,tempfile
from sunset.data import session,geography
from .data import cycles,gefs_frame,refs_frame
from .render import render,PRODUCTS

ROOT=Path(__file__).resolve().parent.parent


def iso(time):return time.isoformat(timespec='seconds').replace('+00:00','Z')


def run():
    now=datetime.now(timezone.utc);cache=ROOT/'.cache/ensembles';cache.mkdir(parents=True,exist_ok=True)
    output=ROOT/'generated/ensembles';output.mkdir(parents=True,exist_ok=True)
    with session() as http:geo=geography(http,ROOT/'.cache/sunset')
    with tempfile.TemporaryDirectory(dir=output) as temp:
        temp=Path(temp);models=[]
        for name,fetch,hours in [('refs',refs_frame,list(range(6,61,6))),('gefs',gefs_frame,list(range(24,385,24)))]:
            errors=[];selected=None
            for cycle in cycles(now):
                try:
                    logging.info('Checking complete %s cycle %s through F%s',name,iso(cycle),hours[-1])
                    fetch(cache,cycle,hours[-1]);selected=cycle;break
                except Exception as exc:errors.append(str(exc));logging.warning('%s cycle incomplete: %s',name,exc)
            if selected is None:raise RuntimeError('No complete recent '+name+' cycle: '+'; '.join(errors))
            frames=[]
            for hour in hours:
                logging.info('Generating %s F%03d',name,hour)
                fields,grid,details=fetch(cache,selected,hour);images={}
                for product,values in fields.items():
                    filename=f'{name}-{selected:%Y%m%d%H}-f{hour:03d}-{product}.png';path=temp/filename
                    readout=render(path,ROOT,name,selected,hour,product,values,grid,details,geo)
                    end=selected+timedelta(hours=hour);start=end-timedelta(hours=6) if product.startswith('rain') else end
                    images[product]=dict(image_filename=filename,image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        valid_start_utc=iso(start),valid_end_utc=iso(end),accumulation_hours=6 if product.startswith('rain') else 0,
                        probability_kind='Neighborhood' if name=='refs' and product=='rain1' else 'Pointwise',readout=readout)
                frames.append(dict(forecast_hour=hour,valid_time_utc=iso(selected+timedelta(hours=hour)),images=images,**details))
            models.append(dict(id=name,label=name.upper(),model_run=iso(selected),native_resolution='3 km' if name=='refs' else '0.5°',
                maximum_forecast_hour=hours[-1],published_step_hours=6 if name=='refs' else 24,
                products=[dict(id=id,label=value[0],description=value[1]) for id,value in PRODUCTS[name].items()],frames=frames))
        result=dict(schema_version=1,generated_at_utc=iso(datetime.now(timezone.utc)),image_width=2000,image_height=1125,models=models,
            notes=['GEFS uses every member: c00 and p01–p30 from one cycle; incomplete sets are rejected.',
                'REFS probabilities are read from NOAA; the number of contributing members can change with forecast hour.',
                'GEFS precipitation probabilities cover individual six-hour windows sampled once per day, not cumulative totals or daily rain chances.',
                'REFS rainfall uses the publisher neighborhood processing. CAPE and freezing are point probabilities.',
                'Raw ensemble guidance is not an official NWS warning or a calibrated forecast.'])
        manifest=temp/'latest.json';manifest.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        for path in temp.iterdir():
            if path.name!='latest.json':os.replace(path,output/path.name)
        os.replace(manifest,output/'latest.json')
    print('Published REFS through 60 hours and GEFS through 384 hours',flush=True)
    return result


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    try:run()
    except Exception:logging.exception('Ensemble refresh failed; previous publication retained');raise SystemExit(1)
