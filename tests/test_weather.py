from datetime import datetime, timezone
import importlib
from pathlib import Path
import json

import numpy as np
import pytest
from scipy.spatial import cKDTree

from weather.sources import wmo_time,validate_spc,sample_ndfd,parse_iso

UTC=timezone.utc
NOW=datetime(2026,10,30,7,tzinfo=UTC)
TEXT='SPC AC 300600\nDay 1 Convective Outlook\nValid 301200Z - 311200Z\n...SUMMARY...\nNo severe thunderstorm areas are forecast.\n\nMore discussion.'


def test_wmo_date_crosses_month_and_year():
    assert wmo_time('010600',datetime(2026,12,31,20,tzinfo=UTC))==datetime(2027,1,1,6,tzinfo=UTC)
    assert wmo_time('312300',datetime(2027,1,1,1,tzinfo=UTC))==datetime(2026,12,31,23,tzinfo=UTC)


def test_empty_spc_outlook_retains_real_valid_times():
    records,meta=validate_spc({'type':'FeatureCollection','features':[]},TEXT,1,NOW)
    assert records==[]
    assert meta['valid_start_utc']=='2026-10-30T12:00:00Z'
    assert meta['valid_end_utc']=='2026-10-31T12:00:00Z'
    assert 'No severe' in meta['summary']


def feature(label='MRGL',issue='202610300600'):
    return {'type':'Feature','properties':{'LABEL':label,'ISSUE':issue,'VALID':'202610301200','EXPIRE':'202610311200'},
       'geometry':{'type':'Polygon','coordinates':[[[-100,30],[-99,30],[-99,31],[-100,30]]]}}


def test_spc_never_relabels_unknown_categories():
    with pytest.raises(ValueError,match='category'):
        validate_spc({'type':'FeatureCollection','features':[feature('NEW-RISK')]},TEXT,1,NOW)


def test_spc_rejects_mixed_issuances():
    with pytest.raises(ValueError,match='different issuances'):
        validate_spc({'type':'FeatureCollection','features':[feature(issue='202610300500')]},TEXT,1,NOW)


def test_expired_spc_is_not_presented_as_current():
    with pytest.raises(ValueError,match='expired'):
        validate_spc({'type':'FeatureCollection','features':[]},TEXT,1,datetime(2026,10,31,13,tzinfo=UTC))


def test_ndfd_nearest_sampling_does_not_extrapolate_across_data_gaps():
    tree=cKDTree([[-80,35],[-81,36]])
    result=sample_ndfd(tree,np.array([20.,80.]),np.array([35.,36.]),np.array([-81.,-80.]))
    assert result[0,1]==20
    assert result[1,0]==80
    assert np.isnan(result[0,0])
    assert np.isnan(result[1,1])


def test_weather_download_failure_preserves_existing_manifest(tmp_path,monkeypatch):
    pipeline=importlib.import_module('weather.__main__')
    fake_root=tmp_path
    output=fake_root/'generated/weather';output.mkdir(parents=True)
    old=output/'latest.json';old.write_text('{"previous":true}')
    monkeypatch.setattr(pipeline,'ROOT',fake_root)
    def broken(*args):raise RuntimeError('upstream failed')
    monkeypatch.setattr(pipeline,'geography',broken)
    with pytest.raises(RuntimeError,match='upstream'):
        pipeline.run()
    assert json.loads(old.read_text())=={'previous':True}
