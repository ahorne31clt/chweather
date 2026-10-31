import csv,io
from datetime import datetime,timezone
import numpy as np
import pytest
from analysis.data import parse_metars,humidity


def test_metar_times_duplicates_cloud_layers_and_missing_pressure():
    header=['station_id','observation_time','latitude','longitude','raw_text','temp_c','dewpoint_c','wind_speed_kt','wind_dir_degrees','altim_in_hg','sea_level_pressure_mb','sky_cover','sky_cover']
    output=io.StringIO();writer=csv.writer(output);writer.writerow(header)
    writer.writerow(['KCLT','2026-10-30T12:53:00Z',35.2,-80.9,'TEST METAR',20,10,5,180,30.01,'','FEW','OVC'])
    writer.writerow(['KCLT','2026-10-30T12:00:00Z',35.2,-80.9,'OLDER METAR',15,5,0,0,30.01,1013,'CLR',''])
    writer.writerow(['KOLD','2026-10-30T08:00:00Z',35,-80,'OLD',10,5,5,180,30,1013,'CLR',''])
    writer.writerow(['KFUT','2026-10-30T15:00:00Z',35,-80,'FUTURE',10,5,5,180,30,1013,'CLR',''])
    stations=parse_metars(output.getvalue(),datetime(2026,10,30,13,tzinfo=timezone.utc),datetime(2026,10,30,12,tzinfo=timezone.utc))
    assert len(stations)==1
    assert stations[0]['raw']=='TEST METAR'
    assert stations[0]['sky_fraction']==1
    assert stations[0]['slp_hpa'] is None
    assert stations[0]['altimeter_inhg']==30.01


def test_derived_humidity_limits_and_saturation():
    assert humidity(np.array([293.15]),np.array([293.15]))[0]==pytest.approx(100)
    values=humidity(np.array([293.15,293.15]),np.array([283.15,298.15]))
    assert 50<values[0]<55
    assert values[1]==100
