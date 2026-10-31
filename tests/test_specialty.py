from datetime import datetime,timezone,timedelta
import json
import numpy as np
import pytest
from specialty.science import accumulate,index_score,frost_categories,mean_where,solar_altitude
from specialty.data import convert_field,parse_front_time,window,normalize_scan
from specialty.config import PRODUCTS
from specialty import __main__ as pipeline


def test_snow_and_flat_ice_use_their_own_physical_units():
    assert convert_field('snow',np.array([.0254]))[0]==pytest.approx(1)
    assert convert_field('ice',np.array([2.54]))[0]==pytest.approx(.1)
    assert convert_field('temp',np.array([273.15]))[0]==pytest.approx(32)
    assert convert_field('wind',np.array([10]))[0]==pytest.approx(22.36936292)


def test_alternating_grib_rows_are_restored_before_geographic_sampling():
    stored=np.array([[1.,2.,3.],[6.,5.,4.],[7.,8.,9.],[12.,11.,10.]])
    expected=np.arange(1.,13.).reshape(4,3)
    assert np.array_equal(normalize_scan(stored,1),expected)
    assert np.array_equal(normalize_scan(stored,0),stored)
    assert stored[1].tolist()==[6.,5.,4.]
    with pytest.raises(ValueError,match='Column-major'):normalize_scan(stored,0,1)


def test_consecutive_accumulations_are_added_without_overlap_or_reset():
    pieces=[(12,18,np.array([1.,np.nan])),(18,24,np.array([2.,1.])),(24,30,np.array([3.,1.])),(30,36,np.array([4.,1.]))]
    result=accumulate(pieces,12,36)
    assert result[0]==10 and np.isnan(result[1])
    with pytest.raises(ValueError,match='consecutive'):accumulate(pieces+[pieces[-1]],12,36)
    with pytest.raises(ValueError,match='cover'):accumulate(pieces[:-1],12,36)


def test_daytime_indices_penalize_rain_and_uncomfortable_conditions():
    t=np.array([70.,70.,95.]);rh=np.array([50.,50.,90.]);w=np.array([5.,5.,25.]);p=np.array([0.,80.,80.]);g=np.array([10.,10.,40.])
    for kind in ('comfort','outdoor'):
        score=index_score(kind,t,rh,w,p,g)
        assert score[0]>score[1]>score[2] and np.all((score>=0)&(score<=100))
    assert mean_where(np.array([[90.,20.],[10.,80.]]),np.array([[True,False],[False,True]])).tolist()==[90,80]


def test_frost_and_freeze_thresholds_are_distinct():
    temp=np.array([[27.,32.,35.,35.,40.]])
    rh=np.array([[90.,90.,90.,50.,90.]]);wind=np.full(temp.shape,3.);cloud=np.full(temp.shape,20.)
    assert frost_categories(temp,rh,wind,cloud,np.ones(temp.shape,dtype=bool)).tolist()==[3,2,1,0,0]
    assert np.isnan(frost_categories(temp,rh,wind,cloud,np.zeros(temp.shape,dtype=bool))).all()


def test_wpc_valid_times_preserve_the_explicit_source_time_zone():
    assert parse_front_time('8pm EDT Sat Oct 31 2026')==datetime(2026,11,1,0,tzinfo=timezone.utc)
    assert parse_front_time('8pm EST Sun Nov 01 2026')==datetime(2026,11,2,1,tzinfo=timezone.utc)


def test_next_utc_day_window_stays_exactly_24_hours_across_month_boundary():
    run=datetime(2026,10,31,12,tzinfo=timezone.utc);now=run+timedelta(hours=8)
    assert window(now,run)==(12,36)
    assert solar_altitude(datetime(2026,3,20,12,tzinfo=timezone.utc),np.array([0.]),np.array([0.]))[0]>85
    assert solar_altitude(datetime(2026,3,20,0,tzinfo=timezone.utc),np.array([0.]),np.array([0.]))[0]<-85


def test_confidence_is_temperature_percentile_spread_not_probability():
    class Reader:
        run=datetime(2026,10,31,12,tzinfo=timezone.utc)
        def fetch(self,hour,name,percentile):return np.array([40.,50.]) if percentile==10 else np.array([45.,65.])
    values,meta,_=pipeline.calculate('confidence',Reader(),12,36,np.array([35.,40.]),np.array([-80.,-100.]))
    assert values.tolist()==[5.,15.]
    assert meta['confidence_valid_at_utc']=='2026-11-01T12:00:00Z'
    assert PRODUCTS['confidence']['unit']=='°F spread'


def test_new_outlook_failures_do_not_replace_existing_successful_manifest(tmp_path,monkeypatch):
    monkeypatch.setattr(pipeline,'ROOT',tmp_path)
    folder=tmp_path/'generated/specialty-snow';folder.mkdir(parents=True);old=folder/'latest.json';old.write_text('{"previous":true}')
    def broken(*args):raise RuntimeError('source unavailable fixture')
    monkeypatch.setattr(pipeline,'geography',broken)
    with pytest.raises(RuntimeError):pipeline.run('snow')
    assert json.loads(old.read_text())=={'previous':True}
