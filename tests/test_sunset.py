from datetime import date, datetime, timezone
from pathlib import Path
import importlib
import json
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import box

from sunset.model import solar_sunset, quality_score, haversine, calculate, top_locations
from sunset.data import candidate_runs, read_grib, download


def test_sunset_longitude_and_season():
    day=date(2026,3,20)
    a,_=solar_sunset(day,0,0)
    b,_=solar_sunset(day,0,-90)
    assert 18 < a < 18.4
    assert b-a == pytest.approx(6,abs=.03)
    summer,az_summer=solar_sunset(date(2026,6,21),35.23,-80.84)
    winter,az_winter=solar_sunset(date(2026,12,21),35.23,-80.84)
    assert summer-winter > 2
    assert az_summer > 270 > az_winter


def test_cloud_and_horizon_physics():
    favorable=quality_score(0,.1,.6,0,20000)
    assert favorable > quality_score(.9,.1,.6,0,20000)
    assert favorable > quality_score(0,.1,.6,.9,20000)
    assert favorable > quality_score(0,0,0,0,20000)
    assert favorable > quality_score(0,.1,.6,0,1000)
    rng=np.random.default_rng(11)
    scores=quality_score(*rng.random((4,1000)),rng.random(1000)*30000)
    assert np.all((scores>=0)&(scores<=100))


def test_local_sunset_time_interpolation():
    lat=np.array([20,24,35,50,54.])
    lon=np.array([-132,-125,-100,-66,-62.])
    shape=(2,len(lat),len(lon))
    fields={'low':np.zeros(shape),'middle':np.zeros(shape),'high':np.zeros(shape),
            'visibility':np.full(shape,20000.)}
    fields['high'][0]=.2;fields['high'][1]=.6
    _,hours,sampled=calculate(date(2026,10,30),lat,lon,np.array([18.,30.]),fields)
    assert sampled['high'] == pytest.approx(.2+(hours-18)/12*.4)
    # Different longitudes use different sunset times, not one CONUS-wide hour.
    assert sampled['high'][1,0] > sampled['high'][1,-1]
    with pytest.raises(ValueError,match='bracket'):
        calculate(date(2026,10,30),lat,lon,np.array([18.,19.]),fields)


def test_land_only_maxima_and_separation():
    lat=np.arange(25,50,.5);lon=np.arange(-124,-67,.5)
    yy,xx=np.meshgrid(lat,lon,indexing='ij')
    score=np.full(yy.shape,50.)
    score[10,10]=99;score[10,11]=98;score[20,50]=97;score[30,90]=96
    mask=np.ones(score.shape,dtype=bool)
    mask[0,0]=False;score[0,0]=100
    picks=top_locations(score,lat,lon,mask,[{'name':'Test reference','lat':35,'lon':-100}],
                        np.full(score.shape,24.),date(2026,10,30))
    assert [p['score'] for p in picks]==[99,97,96]
    for i,a in enumerate(picks):
        for b in picks[i+1:]:
            assert haversine(a['latitude'],a['longitude'],b['latitude'],b['longitude'])>=600


def test_corrupt_grib_is_rejected(tmp_path):
    path=tmp_path/'corrupt.grib2';path.write_bytes(b'not a GRIB file')
    with pytest.raises(ValueError,match='GRIB|Missing GFS'):
        read_grib(path,datetime(2026,10,30,tzinfo=timezone.utc),21)


def test_download_limits_and_cleanup(tmp_path):
    class Response:
        url='https://example.test/weather'
        def __enter__(self):return self
        def __exit__(self,*_):return False
        def raise_for_status(self):pass
        def iter_content(self,_):yield b'123456'
    class Http:
        def get(self,*_,**__):return Response()
    target=tmp_path/'weather.grib2'
    with pytest.raises(ValueError,match='exceeded'):
        download(Http(),'https://example.test/weather',target,maximum=5)
    assert not target.exists()
    assert not target.with_suffix('.grib2.part').exists()


def test_future_run_fails_nonzero_without_replacing_output(tmp_path):
    (tmp_path/'latest.png').write_bytes(b'previous successful image')
    result=subprocess.run([sys.executable,'-m','sunset','--run','2099010100',
                           '--output-dir',str(tmp_path),'--cache-dir',str(tmp_path/'cache')],
                          capture_output=True,text=True,timeout=30)
    assert result.returncode != 0
    assert (tmp_path/'latest.png').read_bytes()==b'previous successful image'
    assert not (tmp_path/'latest.json').exists()


@pytest.mark.parametrize('stage',['processing','rendering'])
def test_processing_and_render_failure_preserve_last_success(tmp_path,monkeypatch,stage):
    pipeline=importlib.import_module('sunset.__main__')
    lat=np.arange(20,54.01,.25);lon=np.arange(-132,-61.99,.25)
    shape=(105,237)
    monkeypatch.setattr(pipeline,'fetch_forecast',lambda *_: (
        datetime.now(timezone.utc),{},np.array([18.,30.]),{},[]))
    monkeypatch.setattr(pipeline,'geography',lambda *_: (box(-125,24,-66,50),[],[]))
    def calculation(*_):
        if stage=='processing':raise ValueError('deliberate processing failure')
        yy,xx=np.meshgrid(np.linspace(24,50,shape[0]),np.linspace(-125,-66,shape[1]),indexing='ij')
        return yy,xx,np.full(shape,50.),np.full(shape,24.),np.ones(shape,dtype=bool),1.,None,None,None
    monkeypatch.setattr(pipeline,'calculate',calculation)
    def bad_render(*_):raise RuntimeError('deliberate rendering failure')
    monkeypatch.setattr(pipeline,'render',bad_render)
    (tmp_path/'latest.png').write_bytes(b'previous image')
    (tmp_path/'latest.json').write_text('{"previous":true}')
    args=SimpleNamespace(date='2026-10-30',run=None,cache_dir=tmp_path/'cache',output_dir=tmp_path)
    with pytest.raises((ValueError,RuntimeError),match='deliberate'):
        pipeline.run(args)
    assert (tmp_path/'latest.png').read_bytes()==b'previous image'
    assert json.loads((tmp_path/'latest.json').read_text())=={'previous':True}


def test_ready_run_fallback_is_bounded():
    now=datetime(2026,10,30,12,tzinfo=timezone.utc)
    cycles=candidate_runs(now)
    assert [r.hour for r in cycles]==[6,0,18]
    assert all((now-r).total_seconds()<86400 for r in cycles)


def test_hrrr_extended_cycles_cover_next_utc_day_and_reject_short_cycles():
    from sunset.hrrr import candidate_runs, required_leads
    now=datetime(2026,6,21,12,tzinfo=timezone.utc)
    runs=candidate_runs(now)
    assert [r.hour for r in runs]==[6,0,18]
    lat,lon=np.meshgrid(np.arange(24,50.01,.25),np.arange(-125,-65.99,.25),indexing='ij')
    hours,_=solar_sunset(date(2026,6,21),lat,lon)
    assert hours.max()>24
    for run in runs:
        leads,offset=required_leads(run,date(2026,6,21),hours.min(),hours.max())
        assert leads[0]-offset < hours.min()
        assert leads[-1]-offset > hours.max()
        assert leads[-1]<=48
        assert np.all(np.diff(leads)==1)
    with pytest.raises(ValueError,match='48-hour'):
        required_leads(now.replace(hour=7),date(2026,6,21),21,29)
    with pytest.raises(ValueError,match='48-hour'):
        required_leads(now,date(2026,6,23),21,29)


def test_hrrr_missing_fields_rejected(tmp_path):
    from sunset.hrrr import read_grib
    path=tmp_path/'empty.grib2';path.write_bytes(b'')
    with pytest.raises(ValueError,match='Missing required HRRR'):
        read_grib(path,datetime(2026,10,30,6,tzinfo=timezone.utc),20)
