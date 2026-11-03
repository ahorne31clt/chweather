from datetime import datetime,timezone
import numpy as np
from optics.science import score,geometry,sample
from optics.data import cycles


def inputs():
    lat=np.arange(20,54.01,.25);lon=np.arange(-132,-61.99,.25)
    shape=(len(lat),len(lon));constant=lambda v:np.full(shape,v,dtype=float)
    fields={k:constant(v) for k,v in dict(low=0,middle=0,high=50,visibility=20000,rate=0,rain=1).items()}
    for p in (300,400,500):
        fields.update({f'temp{p}':constant(235),f'rh{p}':constant(90),f'ice{p}':constant(1e-5)})
    return fields,lat,lon


def test_geometry_masks_arcs_and_night():
    fields,lat,lon=inputs();time=datetime(2026,11,2,17,tzinfo=timezone.utc)
    values,alt=score(fields,time,lat,lon)
    assert np.all(values['zenithal'][alt>=32]==0)
    assert np.all(values['horizontal'][alt<=58]==0)
    assert np.all(values['rainbow'][alt>=42]==0)
    night,_=score(fields,datetime(2026,11,2,5,tzinfo=timezone.utc),lat,lon)
    for field in night.values():assert np.nanmax(field)==0


def test_halo_needs_high_cloud_cold_ice_environment_and_visible_sun():
    fields,lat,lon=inputs();time=datetime(2026,11,2,17,tzinfo=timezone.utc)
    baseline,_=score(fields,time,lat,lon);assert np.nanmax(baseline['halo'])>0
    fields['high'][:]=0
    assert np.nanmax(score(fields,time,lat,lon)[0]['halo'])==0
    fields['high'][:]=50;fields['low'][:]=100
    assert np.nanmax(score(fields,time,lat,lon)[0]['halo'])==0
    fields['low'][:]=0
    for p in (300,400,500):fields[f'temp{p}'][:]=280
    assert np.nanmax(score(fields,time,lat,lon)[0]['halo'])==0


def test_rainbow_needs_liquid_rain_and_is_bounded():
    fields,lat,lon=inputs();time=datetime(2026,11,2,13,tzinfo=timezone.utc)
    assert np.nanmax(score(fields,time,lat,lon)[0]['rainbow'])==0
    fields['rate'][:]=.001
    values,_=score(fields,time,lat,lon)
    assert np.nanmax(values['rainbow'])>0
    for value in values.values():assert 0<=np.nanmin(value)<=np.nanmax(value)<=100
    fields['rain'][:]=0
    assert np.nanmax(score(fields,time,lat,lon)[0]['rainbow'])==0


def test_viewing_rays_do_not_wrap_across_grid_edges():
    fields,lat,lon=inputs();az=np.full(fields['high'].shape,np.pi/2)
    sampled=sample(fields['high'],lat,lon,az,100)
    assert np.isnan(sampled[:,-1]).all()
    assert np.isfinite(sampled[:,10:-10]).all()


def test_directional_sampling_follows_sunward_and_antisolar_sectors():
    fields,lat,lon=inputs();northward=np.zeros(fields['high'].shape)
    gradient=np.broadcast_to(lat[:,None],fields['high'].shape)
    north=sample(gradient,lat,lon,northward,25)
    south=sample(gradient,lat,lon,northward+np.pi,25)
    assert np.nanmean(north[10:-10]-south[10:-10])>0.4


def test_cycles_are_recent_and_six_hourly():
    now=datetime(2026,11,2,14,10,tzinfo=timezone.utc)
    choices=cycles(now)
    assert choices[0].hour==6
    assert all(5<=(now-t).total_seconds()/3600<24 for t in choices)
