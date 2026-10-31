"""Generate bounded real-data GFS/HRRR frame sets: python -m models."""
import argparse
from datetime import datetime,timezone,timedelta
from pathlib import Path
import logging
import json
import hashlib
import os
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

from sunset.data import session,geography
from .data import candidate_cycles,fetch_frame
from .generation import render_products,init_renderer,render_cached
from .fields import PRODUCTS,parameter_metadata
from .render import region_presets

ROOT=Path(__file__).resolve().parent.parent
LOG=logging.getLogger('models')


def iso(value):return value.isoformat(timespec='seconds').replace('+00:00','Z')


def frame_hours(end,step):
    if end<0 or step<1 or end%step:raise ValueError('End hour must be nonnegative and divisible by step')
    return list(range(0,end+1,step))


def cycle_plans(model,now,end,step):
    hours=frame_hours(end,step)
    if model=='hrrr' and end>18:
        # Extended forecasts are issued only at 00/06/12/18 UTC.
        plans=[(cycle,hours) for cycle in candidate_cycles(model,now,extended=True)]
        fallback=frame_hours(18,step)
        plans.extend((cycle,fallback) for cycle in candidate_cycles(model,now))
        return plans
    return [(cycle,hours) for cycle in candidate_cycles(model,now)]


def run(args):
    now=datetime.now(timezone.utc)
    cache=ROOT/'.cache/models';cache.mkdir(parents=True,exist_ok=True)
    output=ROOT/'generated/models';output.mkdir(parents=True,exist_ok=True)
    specs=[('gfs',cycle_plans('gfs',now,args.gfs_end,args.gfs_step)),
           ('hrrr',cycle_plans('hrrr',now,args.hrrr_end,args.hrrr_step)),
           ('nam',cycle_plans('nam',now,getattr(args,'nam_end',84),3))]
    if getattr(args,'model',None):specs=[spec for spec in specs if spec[0]==args.model]
    results=[]
    with session() as http,tempfile.TemporaryDirectory(dir=output) as staging:
        staging=Path(staging)
        usa,countries,states=geography(http,ROOT/'.cache/sunset')
        geo=dict(usa=usa,countries=countries,states=states)
        for model,plans in specs:
            errors=[];success=None
            for cycle,hours in plans:
                try:
                    # Probe the last frame before downloading a whole incomplete cycle.
                    fetch_frame(http,cache,model,cycle,hours[-1]);time.sleep(1)
                    frames=[];grid_id=None;total_bytes=0;pending=[];regions=None
                    workers=getattr(args,'workers',1)
                    pool=ProcessPoolExecutor(max_workers=workers,initializer=init_renderer,initargs=(geo,)) if workers>1 else None
                    try:
                        for hour in hours:
                            fields,grid,url,size=fetch_frame(http,cache,model,cycle,hour)
                            if grid_id is not None and grid['id']!=grid_id:raise ValueError('Model grid changed within a cycle')
                            grid_id=grid['id'];total_bytes+=size
                            if regions is None:regions=region_presets(grid)
                            if pool:
                                pending.append(pool.submit(render_cached,staging,ROOT,model,cycle,hour,url))
                                if len(pending)>=workers:
                                    frames.append(pending.pop(0).result())
                                    LOG.info('Rendered %s F%03d / %d products',model.upper(),frames[-1]['hour'],len(frames[-1]['images']))
                            else:
                                frames.append(render_products(staging,ROOT,model,cycle,hour,fields,grid,geo,url))
                                LOG.info('Rendered %s F%03d / %d products',model.upper(),hour,len(frames[-1]['images']))
                            del fields
                            time.sleep(1)
                        frames.extend(future.result() for future in pending)
                    finally:
                        if pool:pool.shutdown(wait=True,cancel_futures=True)
                    success=dict(id=model,name=model.upper(),status='available',model_run=iso(cycle),
                        frames=frames,forecast_step_hours={'gfs':args.gfs_step,'hrrr':args.hrrr_step,'nam':3}[model],
                        forecast_end_hour=hours[-1],requested_end_hour={'gfs':args.gfs_end,'hrrr':args.hrrr_end,'nam':getattr(args,'nam_end',84)}[model],regions=regions,
                        extended_run=model=='hrrr' and hours[-1]>18,
                        native_resolution={'gfs':'0.25 degrees','hrrr':'3 km','nam':'12 km'}[model],
                        downloaded_subset_bytes=total_bytes,pressure_field='MSLMA (MAPS reduction)' if model=='hrrr' else 'PRMSL',
                        input_fields=(['CRAIN','CSNOW','CFRZR','CICEP','PRATE'] if model!='nam' else [])+['TMP 2 m','DPT 2 m','RH 2 m','CAPE surface','UGRD 10 m','VGRD 10 m','UGRD 500 mb','VGRD 500 mb','ABSV 500 mb','HGT 500 mb','HGT 1000 mb','MSLMA' if model=='hrrr' else 'PRMSL'])
                    break
                except Exception as error:
                    LOG.warning('%s %s unavailable: %s',model,cycle.isoformat(),error)
                    errors.append(str(error))
            results.append(success or dict(id=model,name=model.upper(),status='unavailable',
                message='No complete recent model cycle could be downloaded and rendered.',errors=errors))
        available=[result for result in results if result['status']=='available']
        if not available:raise RuntimeError('Neither model produced a complete usable cycle')
        manifest=dict(schema_version=2,generated_at_utc=iso(datetime.now(timezone.utc)),models=results,
            product='Precipitation, pressure, 2 m temperature/dewpoint, 500 mb heights/wind/absolute vorticity',
            products=parameter_metadata(),
            image_width=2400,image_height=1350,
            rate_units='mm/hour liquid equivalent',minimum_rate_mm_hour=.1,
            pressure_contour_interval_hpa=4,thickness_contour_interval_dam=6,
            notes=['Numerical model guidance, not observations or official warnings.',
                'Precipitation type comes from the model categorical flags, not a 540-dam threshold.',
                'Mixed flags means more than one categorical flag is active; unclassified means a rate without an active flag.',
                'Surface pressure is displayed as mean sea-level pressure; HRRR uses the MAPS reduction.',
                'H/L symbols mark selected broad closed extrema in smoothed mean sea-level pressure; values are hPa.',
                'Temperature/dewpoint are Fahrenheit, wind speed is knots, heights are decameters, absolute vorticity is 10^-5 s^-1.',
                'Pointer readouts are nearest native samples on a 4-image-pixel display grid, not observations or exact address forecasts.',
                'Only the published forecast hours and latest complete selected cycle are available.'])
        manifest_path=staging/'latest.json'
        manifest_path.write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        keep={'latest.json'}
        for result in available:
            for frame in result['frames']:
                for image in frame['images'].values():
                    filename=image['image_filename'];keep.add(filename)
                    os.replace(staging/filename,output/filename)
                    if image.get('overlay_filename'):
                        filename=image['overlay_filename'];keep.add(filename);os.replace(staging/filename,output/filename)
                if frame.get('readouts'):
                    filename=frame['readouts']['filename'];keep.add(filename)
                    os.replace(staging/filename,output/filename)
        os.replace(manifest_path,output/'latest.json')
        # Only remove this generator's obsolete frames, within the fixed output directory.
        for path in output.iterdir():
            if path.suffix not in ('.png','.bin','.webp') and not path.name.endswith('.bin.gz'):continue
            if path.name not in keep and path.name.startswith(tuple(name+'-' for name,_ in specs)):path.unlink()
    LOG.info('Published %d model cycles, %d frames',len(available),sum(len(r['frames']) for r in available))
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',choices=['gfs','hrrr','nam'],help='Generate one independent model job; default generates all three')
    parser.add_argument('--gfs-end',type=int,choices=range(0,385),default=384)
    parser.add_argument('--gfs-step',type=int,choices=[3,6,12],default=3)
    parser.add_argument('--hrrr-end',type=int,choices=range(0,49),default=48)
    parser.add_argument('--hrrr-step',type=int,choices=[1,2,3,6],default=1)
    parser.add_argument('--nam-end',type=int,choices=list(range(0,85,3)),default=84)
    parser.add_argument('--workers',type=int,choices=[1,2],default=2,help='Bounded render processes (use 1 on a small machine)')
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    try:
        run(args)
        from .airports import generate
        if args.model!='nam':generate()
    except Exception:
        LOG.exception('Model generation failed; no synthetic frames substituted')
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
