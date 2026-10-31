"""Refresh universal probes and sharp annotation layers from published model runs."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ProcessPoolExecutor
import hashlib,json,os,tempfile,logging
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from sunset.data import session,geography
from .data import fetch_frame
from .render import render,projection_for,native_axes,write_readouts
from .generation import init_renderer

ROOT=Path(__file__).resolve().parent.parent


def refresh_frame(task):
    import models.generation as generation
    staging,model,cycle,hour,products=task
    with session() as http:fields,grid,_,_=fetch_frame(http,ROOT/'.cache/models',model,cycle,hour)
    projection=projection_for(grid);fig=plt.figure(figsize=(16,9))
    try:
        ax=fig.add_axes([.004,.055,.992,.874],projection=projection);ax.set_extent([-126,-65,23.5,50.5],crs=ccrs.PlateCarree())
        if grid['type']=='lambert':x,y=native_axes(grid,projection);source=projection
        else:x,y=grid['longitudes'],grid['latitudes'];source=ccrs.PlateCarree()
        stem=f'{model}-{cycle:%Y%m%d%H}-f{hour:03d}'
        readouts=write_readouts(Path(staging)/(stem+'.png'),ax,fields,x,y,source,projection)
        readouts['sha256']=hashlib.sha256((Path(staging)/readouts['filename']).read_bytes()).hexdigest()
    finally:plt.close(fig)
    overlays={}
    for product in products:
        if product=='precip':continue
        filename=stem+'-'+product+'.png'
        result=render(Path(staging)/filename,ROOT,model,cycle,hour,fields,grid,generation.RENDER_GEO,product,overlay_only=True)
        overlay=result['overlay']['filename']
        overlays[product]=dict(overlay_filename=overlay,overlay_sha256=hashlib.sha256((Path(staging)/overlay).read_bytes()).hexdigest())
    return model,hour,readouts,overlays


def main(probes_only=False):
    output=ROOT/'generated/models';manifest=json.loads((output/'latest.json').read_text(encoding='utf-8'))
    with session() as http,tempfile.TemporaryDirectory(dir=output) as staging:
        usa,countries,states=geography(http,ROOT/'.cache/sunset');geo=dict(usa=usa,countries=countries,states=states)
        tasks=[(staging,m['id'],datetime.fromisoformat(m['model_run'].replace('Z','+00:00')),f['hour'],[] if probes_only else list(f['images'])) for m in manifest['models'] if m['status']=='available' for f in m['frames']]
        with ProcessPoolExecutor(max_workers=2,initializer=init_renderer,initargs=(geo,)) as pool:
            for model,hour,readouts,overlays in pool.map(refresh_frame,tasks):
                frame=next(f for m in manifest['models'] if m['id']==model for f in m['frames'] if f['hour']==hour)
                frame['readouts']=readouts
                for product,extra in overlays.items():frame['images'][product].update(extra)
                print('Universal probe + overlays',model,hour,flush=True)
        for m in manifest['models']:
            for f in m.get('frames',[]):
                filename=f['readouts']['filename'];os.replace(Path(staging)/filename,output/filename)
                for image in f['images'].values():
                    if image.get('overlay_filename'):
                        filename=image['overlay_filename']
                        if (Path(staging)/filename).exists():os.replace(Path(staging)/filename,output/filename)
        manifest['generated_at_utc']=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
        target=Path(staging)/'latest.json';target.write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n',encoding='utf-8');os.replace(target,output/'latest.json')
    print('Published universal model probes and smoothing overlays',flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--probes-only',action='store_true');args=parser.parse_args()
    try:main(args.probes_only)
    except Exception:
        logging.exception('Viewer asset refresh failed; publication was not replaced');raise SystemExit(1)
