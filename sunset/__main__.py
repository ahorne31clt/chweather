"""One command: python -m sunset. Any unhandled pipeline error returns 1."""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from zoneinfo import ZoneInfo

import numpy as np
from shapely import intersects_xy

from .data import session,fetch_forecast,geography
from .model import MODEL_VERSION,MIN_SEPARATION_KM,solar_sunset,calculate,top_locations
from .render import render

ROOT=Path(__file__).resolve().parent.parent
LOG=logging.getLogger('sunset')


def run(args):
    now=datetime.now(timezone.utc)
    day=date.fromisoformat(args.date) if args.date else now.astimezone(ZoneInfo('America/New_York')).date()
    requested=datetime.strptime(args.run,'%Y%m%d%H').replace(tzinfo=timezone.utc) if args.run else None
    cache=Path(args.cache_dir).resolve(); cache.mkdir(parents=True,exist_ok=True)
    output=Path(args.output_dir).resolve(); output.mkdir(parents=True,exist_ok=True)
    # Bound all sunset times on scoring grid, not the download padding.
    target_lat=np.arange(24,50.001,.25); target_lon=np.arange(-125,-65.999,.25)
    mesh_lon,mesh_lat=np.meshgrid(target_lon,target_lat)
    expected_hours,_=solar_sunset(day,mesh_lat,mesh_lon)
    with session() as http:
        model_run,lat,lon,hours,cubes,urls=fetch_forecast(http,cache,day,now,
                   float(expected_hours.min()),float(expected_hours.max()),requested)
        usa,countries,states=geography(http,cache)
    score,sunset_hours,sampled=calculate(day,lat,lon,hours,cubes)
    target_lat=lat[(lat>=24)&(lat<=50)]; target_lon=lon[(lon>=-125)&(lon<=-66)]
    mesh_lon,mesh_lat=np.meshgrid(target_lon,target_lat)
    mask=intersects_xy(usa,mesh_lon,mesh_lat)
    if mask.sum()<5000 or not np.isfinite(score).all():
        raise ValueError('Invalid CONUS mask or output score')
    cities=json.loads((ROOT/'sunset/cities.json').read_text(encoding='utf-8'))
    places=top_locations(score,target_lat,target_lon,mask,cities,sunset_hours,day)
    metadata=dict(schema_version=1,algorithm_version=MODEL_VERSION,product='Experimental sunset color potential',
        model='NOAA/NCEP GFS 0.25 degree',model_run=model_run.isoformat().replace('+00:00','Z'),
        forecast_valid_date=day.isoformat(),valid_timezone_basis='Each location’s sunset on this calendar date',
        generated_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
        image_filename='latest.png',image_width=2400,image_height=1500,
        native_grid_degrees=.25,forecast_valid_times_utc=[
            (datetime(day.year,day.month,day.day,tzinfo=timezone.utc)+timedelta(hours=float(h))).isoformat().replace('+00:00','Z') for h in hours],
        minimum_top_location_separation_km=MIN_SEPARATION_KM,top_locations=places,
        score_range=[0,100],score_is_probability=False,source_urls=urls,
        geography_source='https://www.naturalearthdata.com/',
        limitations=['Uncalibrated heuristic; not a probability or official NWS forecast.',
          'Cloud fraction does not describe optical thickness; sunset cloud errors can dominate.',
          'Does not simulate smoke/aerosol chemistry, three-dimensional radiative transfer, terrain, or buildings.',
          'High-resolution image; meteorological detail remains the native 0.25-degree GFS grid.'])
    # Stage and validate BOTH files before exposing either. JSON is the commit
    # marker; image hash allows consumers to detect a mismatched pair.
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        image=Path(temporary)/'latest.png'; manifest=Path(temporary)/'latest.json'
        render(image,ROOT,target_lat,target_lon,score,mask,usa,countries,states,metadata)
        metadata['image_sha256']=hashlib.sha256(image.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        json.loads(manifest.read_text(encoding='utf-8'))
        os.replace(image,output/'latest.png')
        os.replace(manifest,output/'latest.json')
    LOG.info('Saved %s and %s; run %s',output/'latest.png',output/'latest.json',metadata['model_run'])
    return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',help='Local sunset calendar date YYYY-MM-DD; default today in America/New_York')
    parser.add_argument('--run',help='Optional GFS cycle YYYYMMDDHH; must be recent, complete, not future')
    parser.add_argument('--cache-dir',default=str(ROOT/'.cache/sunset'))
    parser.add_argument('--output-dir',default=str(ROOT/'generated/sunset'))
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    try:
        run(args)
    except Exception:
        LOG.exception('Sunset forecast failed; no synthetic or partial forecast was substituted')
        return 1
    return 0


if __name__=='__main__':
    sys.exit(main())
