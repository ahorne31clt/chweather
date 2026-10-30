"""Importable, spawn-safe rendering workers for Linux and Windows."""
from pathlib import Path
from datetime import timedelta
import hashlib
import requests
from sunset.data import session
from .data import fetch_frame,surface_request_details
from .render import render
from .fields import PRODUCTS,available_products

def iso(value):return value.isoformat(timespec="seconds").replace("+00:00","Z")

def render_products(staging,root,model,cycle,hour,fields,grid,geo,url):
    stem=f'{model}-{cycle:%Y%m%d%H}-f{hour:03d}'
    images={};lookup=None
    for product in available_products(model):
        filename=stem+('' if product=='precip' else '-'+product)+'.png'
        target=Path(staging)/filename
        result=render(target,root,model,cycle,hour,fields,grid,geo,product)
        images[product]=dict(image_filename=filename,image_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
        if isinstance(result,dict):
            lookup=result;lookup['sha256']=hashlib.sha256((Path(staging)/lookup['filename']).read_bytes()).hexdigest()
    frame=dict(hour=hour,valid_time_utc=iso(cycle+timedelta(hours=hour)),**images.get('precip',images['temp2m']),images=images,source_url=url)
    endpoint,query=surface_request_details(model,cycle,hour)
    frame['surface_source_url']=requests.Request('GET',endpoint,params=query).prepare().url
    if model=='hrrr':frame['vorticity_source_url']=f'https://noaa-hrrr-bdp-pds.s3.amazonaws.com/hrrr.{cycle:%Y%m%d}/conus/hrrr.t{cycle:%H}z.wrfprsf{hour:02d}.grib2'
    if lookup:frame['readouts']=lookup
    return frame


def init_renderer(geo):
    global RENDER_GEO
    RENDER_GEO=geo


def render_cached(staging,root,model,cycle,hour,url):
    # Parent validates/downloads first. Children only reread bounded cached data.
    with session() as http:fields,grid,_,_=fetch_frame(http,Path(root)/'.cache/models',model,cycle,hour)
    return render_products(staging,root,model,cycle,hour,fields,grid,RENDER_GEO,url)

