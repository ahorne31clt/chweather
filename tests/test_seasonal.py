from datetime import datetime,timezone
import calendar
import numpy as np
import pytest
from seasonal.science import add_month,seasonal_anomaly,probability_fields,station_statistics,choose_analogs
from seasonal.__main__ import analog_grid


def test_calendar_day_weighted_temperature_and_precipitation():
    assert add_month(2026,12,2)==(2027,2)
    raw=np.array([[[1.]],[[2.]],[[3.]]])
    expected=(31+2*31+3*29)/(31+31+29)*1.8
    assert seasonal_anomaly(raw,(2023,12),'temperature')[0,0]==pytest.approx(expected)
    assert seasonal_anomaly(np.ones((3,1,1)),(2023,12),'precipitation')[0,0]==pytest.approx(91/25.4)
    with pytest.raises(ValueError):seasonal_anomaly(raw[:2],(2023,12),'temperature')


def test_probability_fraction_metadata_quirk_and_invalid_simplex():
    fractions=[np.full((2,2),p) for p in [.5,.3,.2]]
    assert np.allclose(probability_fields(fractions)[:,0,0],[50,30,20])
    assert np.allclose(probability_fields([x*100 for x in fractions])[:,0,0],[50,30,20])
    with pytest.raises(ValueError,match='sum'):probability_fields([np.full((2,2),.6)]*3)
    with pytest.raises(ValueError,match='range'):probability_fields([np.full((2,2),v) for v in [-.1,.5,.6]])


def test_station_normals_cross_year_and_missing_months_never_zero_filled():
    series={(y,m):[10.,1.,2.] for y in range(1949,2027) for m in range(1,13)}
    for y in range(1950,1960):
        for yy,m in [(y,12),(y+1,1),(y+1,2)]:series[yy,m]=[15.,2.,3.]
    selected=[(y,12) for y in range(1950,1960)]
    result=station_statistics(series,(2026,12),selected,'snowfall')
    assert result['normal']==6 and result['anomaly']==3 and result['above']==100
    assert result['normal_years']==30 and result['analog_count']==10
    for y in range(1950,1953):series[y,12]=[np.nan]*3
    assert station_statistics(series,(2026,12),selected,'snowfall') is None


def test_low_snow_climates_are_masked_and_ties_are_not_below():
    series={(y,m):[10.,1.,0.] for y in range(1949,2027) for m in range(1,13)}
    selected=[(y,12) for y in range(1950,1960)]
    assert station_statistics(series,(2026,12),selected,'snowfall') is None
    value=station_statistics(series,(2026,12),selected,'temperature')
    assert value['above']==value['below']==0 and value['equal']==100


def test_analog_selection_deduplicates_persistent_events():
    rows=[]
    for y in range(1950,2027):
        for m in range(1,13):
            v=1.0 if y%4 in (0,1) else -.7
            rows.append(dict(year=y,center_month=m,season='test',anomaly_c=v))
    rows=[r for r in rows if (r['year'],r['center_month'])<=(2026,8)]
    rows[-1]['anomaly_c']=1.2
    latest,selected,phase=choose_analogs(rows,datetime(2026,11,1,tzinfo=timezone.utc))
    assert len(selected)==10 and len({(r['year']-1952)//4 for r in selected})==10
    assert all(r['year']<2026 and r['center_month']==8 for r in selected)


def test_analog_map_smoothly_fills_domain_and_flags_extrapolation():
    points=[dict(lon=-90+i,lat=35+j,above=70) for i in range(3) for j in range(3)]
    grid,support=analog_grid(points,'above',np.array([36,48]),np.array([-89,-120]),True)
    assert grid[0,0]==pytest.approx(70)
    assert np.isfinite(grid).all()
    assert support[1,1]


def test_seasonal_workflow_publishes_independently():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    workflow=(root/'.github/workflows/seasonal.yml').read_text()
    assert 'python -m seasonal' in workflow
    assert 'retention-days: 35' in workflow
    assert 'name: forecast-seasonal' in workflow
    assert 'Seasonal climate outlooks' in (root/'.github/workflows/publish.yml').read_text()


def test_precipitation_rate_source_seconds_are_converted_to_days(tmp_path,monkeypatch):
    import seasonal.data as data
    monkeypatch.setattr(data,'cached',lambda *args,**kwargs:tmp_path/'fixture')
    monkeypatch.setattr(data,'read_netcdf',lambda *args:dict(units={'fcst':'mm/s'},values={'fcst':np.ones((3,1,1))/86400}))
    fields,url=data.model_source(None,tmp_path,'2026100800','CFSv2','precipitation')
    assert np.allclose(fields['values']['fcst'],1)
    assert 'CFSv2.prate.202610' in url


def test_model_source_rejects_unsupported_units(tmp_path,monkeypatch):
    import seasonal.data as data
    monkeypatch.setattr(data,'cached',lambda *args,**kwargs:tmp_path/'fixture')
    monkeypatch.setattr(data,'read_netcdf',lambda *args:dict(units={'fcst':'unknown'},values={'fcst':np.ones((3,1,1))}))
    with pytest.raises(ValueError,match='units'):data.model_source(None,tmp_path,'2026100800','CFSv2','precipitation')


def test_blend_stream_weight_learns_better_guidance_and_preserves_bounds():
    from seasonal.blend import choose_model_weight
    rows=[[float(i%7),float(i%7)+.1,float(i%7)+3,1] for i in range(100)]
    alpha,residual,meta=choose_model_weight(rows)
    assert .9<=alpha<=1
    assert meta['development_cases']==100 and np.isfinite(residual).all()
    with pytest.raises(ValueError,match='Too few'):choose_model_weight(rows[:5])


def test_blend_analog_weights_use_only_candidate_rows_and_normalize():
    from seasonal.blend import analog_weights,weighted_quantile
    x=np.array([[v]*7 for v in range(30)],dtype=float)
    w=analog_weights(x,np.zeros(7),2,k=10)
    assert w.sum()==pytest.approx(1) and np.count_nonzero(w)==10
    assert w[0]>w[9] and w[29]==0
    assert weighted_quantile([0,6,12],[.2,.6,.2],.5)==pytest.approx(3)


def test_measured_zero_snow_climates_are_retained_for_complete_maps():
    series={(y,m):[10.,1.,0.] for y in range(1949,2027) for m in range(1,13)}
    result=station_statistics(series,(2026,12),[(y,12) for y in range(1950,1960)],'snowfall',include_low_snow=True)
    assert result['normal']==result['anomaly']==0
    assert result['above']==result['below']==0 and result['equal']==100


def test_blend_pipeline_excludes_unobserved_target_months():
    from seasonal.blend import calculate,MODELS
    series={(y,m):[45+np.sin(y*.7),2+.3*np.cos(y*.3),1+.6*np.cos(y*.5)] for y in range(1950,2028) for m in range(1,13)}
    stations=[dict(id=str(i),name='Synthetic station',lon=-124+56*(i%10)/9,lat=24+25*(i//10)/7,series=series.copy()) for i in range(80)]
    oni=[dict(year=y,center_month=m,anomaly_c=float(np.sin(y*.2))) for y in range(1950,2027) for m in range(1,13)]
    indices={k:{(y,m):float(np.cos(y*.4)) for y in range(1950,2027) for m in range(1,13)} for k in ['ao','nao','pna']}
    def frame(year,variable):
        return dict(lat=np.array([50.,24.]),lon=np.array([-125.,-66.]),dates=[add_month(year,10,i) for i in range(9)],
                    values={'fcst':np.full((9,2,2),.1 if variable=='temperature' else .01)})
    current={(m,v):frame(2026,v) for m in MODELS for v in ['temperature','precipitation']}
    history={y:{v:frame(y,v) for v in ['temperature','precipitation']} for y in range(2018,2026)}
    first,meta=calculate(stations,(2026,11),(2026,10),current,history,oni,indices)
    assert meta['model_components']==list(MODELS)
    assert all(len(rows)==80 for rows in first.values())
    for record in first['temperature']:
        d=record['drivers'];a=record['model_weight']
        assert record['anomaly']==pytest.approx(a*d['raw_model_anomaly']+(1-a)*d['statistical_anomaly'])
        assert d['bias_adjustment']==0 and d['residual_mean_shift']==0
    for station in stations:
        station['series'][2026,11]=[999,999,999]
        station['series'][2026,12]=[999,999,999]
        station['series'][2027,1]=[999,999,999]
    second,_=calculate(stations,(2026,11),(2026,10),current,history,oni,indices)
    for variable in first:
        assert first[variable][0]['anomaly']==pytest.approx(second[variable][0]['anomaly'])


def test_six_month_snow_season_sums_each_month_once():
    from seasonal.blend import aggregate,references
    series={(y,m):[40.,1.,float(m)] for y in range(1949,2028) for m in range(1,13)}
    value=aggregate(series,(2026,11),6)
    assert value[1]==6
    assert value[2]==11+12+1+2+3+4
    normal,_,counts,_=references(dict(series=series),(2026,11),6)
    assert normal[2]==33 and counts[2]==30
    raw=np.ones((6,1,1))
    expected=sum(calendar.monthrange(y,m)[1] for y,m in [(2026,11),(2026,12),(2027,1),(2027,2),(2027,3),(2027,4)])/25.4
    assert seasonal_anomaly(raw,(2026,11),'precipitation',count=6)[0,0]==pytest.approx(expected)
