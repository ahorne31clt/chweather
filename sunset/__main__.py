"""One command: python -m sunset. Any unhandled pipeline error returns 1."""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import gzip
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from zoneinfo import ZoneInfo

import numpy as np
from shapely import intersects_xy
from shapely.geometry import mapping

from .data import session,geography
from .hrrr import fetch_forecast,calculate
from .model import MODEL_VERSION,MIN_SEPARATION_KM,solar_sunset,top_locations
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
        model_run,grid,hours,cubes,urls=fetch_forecast(http,cache,day,now,
                   float(expected_hours.min()),float(expected_hours.max()),requested)
        usa,countries,states=geography(http,cache)
    target_lat,target_lon,score,sunset_hours,mask,coverage,projection,x,y=calculate(day,grid,hours,cubes,usa)
    del cubes
    if mask.sum()<5000 or not np.isfinite(score[mask]).all():
        raise ValueError('Invalid CONUS mask or output score')
    cities=json.loads((ROOT/'sunset/cities.json').read_text(encoding='utf-8'))
    places=top_locations(score,target_lat,target_lon,mask,cities,sunset_hours,day)
    metadata=dict(schema_version=1,algorithm_version=MODEL_VERSION,product='Experimental sunset color potential',
        model='NOAA/NCEP HRRR 3 km',model_id='hrrr',model_run=model_run.isoformat().replace('+00:00','Z'),
        forecast_valid_date=day.isoformat(),valid_timezone_basis='Each location’s sunset on this calendar date',
        generated_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
        image_filename='latest.png',lookup_filename='lookup.json',image_width=2400,image_height=1500,
        native_grid_km=3,extended_cycle_horizon_hours=48,forecast_interval_hours=1,
        land_ray_coverage_fraction=coverage,forecast_lead_hours_used=[int(round(h+(datetime(day.year,day.month,day.day,tzinfo=timezone.utc)-model_run).total_seconds()/3600)) for h in hours],forecast_valid_times_utc=[
            (datetime(day.year,day.month,day.day,tzinfo=timezone.utc)+timedelta(hours=float(h))).isoformat().replace('+00:00','Z') for h in hours],
        minimum_top_location_separation_km=MIN_SEPARATION_KM,top_locations=places,
        score_range=[0,100],score_is_probability=False,source_urls=urls,
        geography_source='https://www.naturalearthdata.com/',
        limitations=['Uncalibrated heuristic; not a probability or official NWS forecast.',
          'Cloud fraction does not describe optical thickness; sunset cloud errors can dominate.',
          'Does not simulate smoke/aerosol chemistry, three-dimensional radiative transfer, terrain, or buildings.',
          'Meteorological inputs use the native 3-km HRRR grid; higher resolution does not guarantee more accurate sunset colors.',
          'Locations whose full sunward ray is outside the HRRR domain have no score.'])
    # Stage and validate BOTH files before exposing either. JSON is the commit
    # marker; image hash allows consumers to detect a mismatched pair.
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        image=Path(temporary)/'latest.png'; manifest=Path(temporary)/'latest.json'
        render(image,ROOT,target_lat,target_lon,score,mask,usa,countries,states,metadata)
        metadata['image_sha256']=hashlib.sha256(image.read_bytes()).hexdigest()
        # Compact location lookup: nearest native HRRR values on a 0.03-degree
        # geographic lattice. Rendering and rankings retain the native grid.
        from scipy.interpolate import RegularGridInterpolator
        import cartopy.crs as ccrs
        lookup_lat=np.round(np.arange(24,50.001,.03),5)
        lookup_lon=np.round(np.arange(-125,-65.999,.03),5)
        llon,llat=np.meshgrid(lookup_lon,lookup_lat)
        projected=projection.transform_points(ccrs.PlateCarree(),llon,llat)
        points=np.column_stack((projected[...,1].ravel(),projected[...,0].ravel()))
        lookup_score=RegularGridInterpolator((y,x),score,method='nearest',bounds_error=False,fill_value=np.nan)(points).reshape(llat.shape)
        lookup_time=RegularGridInterpolator((y,x),sunset_hours,method='nearest',bounds_error=False,fill_value=np.nan)(points).reshape(llat.shape)*60
        usable=intersects_xy(usa,llon,llat)&np.isfinite(lookup_score)&np.isfinite(lookup_time)
        encoded=np.full((2,*llat.shape),-32768,dtype='<i2')
        encoded[0][usable]=np.rint(lookup_score[usable]*10).astype('<i2')
        encoded[1][usable]=np.rint(lookup_time[usable]).astype('<i2')
        binary=Path(temporary)/'lookup.bin.gz'
        binary.write_bytes(gzip.compress(encoded.tobytes(),compresslevel=6,mtime=0))
        lookup=dict(schema_version=2,model='HRRR 3 km',model_run=metadata['model_run'],
            forecast_valid_date=metadata['forecast_valid_date'],generated_at_utc=metadata['generated_at_utc'],
            image_sha256=metadata['image_sha256'],grid_degrees=.03,native_grid_km=3,
            data_filename='lookup.bin.gz',data_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            encoding='gzip-int16le-two-planes',missing_value=-32768,score_scale=10,
            latitudes=lookup_lat.tolist(),longitudes=lookup_lon.tolist(),
            land_geometry=mapping(usa.simplify(.015,preserve_topology=True)))
        lookup_path=Path(temporary)/'lookup.json'
        lookup_path.write_text(json.dumps(lookup,separators=(',',':'),allow_nan=False),encoding='utf-8')
        metadata['lookup_sha256']=hashlib.sha256(lookup_path.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        json.loads(manifest.read_text(encoding='utf-8'))
        os.replace(image,output/'latest.png')
        os.replace(lookup_path,output/'lookup.json')
        os.replace(binary,output/'lookup.bin.gz')
        os.replace(manifest,output/'latest.json')
    LOG.info('Saved %s and %s; run %s',output/'latest.png',output/'latest.json',metadata['model_run'])
    return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',help='Local sunset calendar date YYYY-MM-DD; default today in America/New_York')
    parser.add_argument('--run',help='Optional extended HRRR cycle YYYYMMDDHH (00/06/12/18Z); must cover all sunsets within 48 hours')
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
