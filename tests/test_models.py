from datetime import datetime,timezone
from types import SimpleNamespace

import cartopy.crs as ccrs
import numpy as np
import pytest

from models.data import candidate_cycles,field_key
from models.product import classify,diagnostics,pressure_centers
from models.render import native_axes,projection_for
from models.__main__ import frame_hours,cycle_plans
from models.fields import scalar_field
from models.fields import available_products,parameter_metadata


def test_precipitation_flags_and_missing_values():
    fields={key:np.zeros((1,8)) for key in ['rain','snow','freezing_rain','sleet']}
    fields['rate']=np.array([[0,.09,.1,2,3,4,5,np.nan]])/3600
    fields['rain'][0,[1,2,6]]=1
    fields['snow'][0,[3,6]]=1
    fields['freezing_rain'][0,4]=1
    fields['sleet'][0,5]=1
    kind,rate,rgba=classify(fields)
    assert kind.tolist()==[[0,0,1,2,3,4,5,0]]
    assert rgba[0,0,3]==0 and rgba[0,7,3]==0
    assert rgba[0,2,3]>0
    fields['rate'][0,0]=1/3600
    assert classify(fields)[0][0,0]==6


def test_pressure_and_layer_thickness_units():
    pressure,thickness=diagnostics(dict(pressure=np.array([101325.]),height500=np.array([5600.]),height1000=np.array([160.])))
    assert pressure[0]==1013.25
    assert thickness[0]==544


def test_pressure_centers_reject_flat_fields_and_open_gradients():
    assert pressure_centers(np.full((80,140),1015.))==[]
    assert pressure_centers(np.tile(np.linspace(995,1035,140),(80,1)))==[]
    assert pressure_centers(np.full((80,140),np.nan))==[]


def test_pressure_centers_find_separated_closed_systems():
    y,x=np.mgrid[:100,:180]
    pressure=1015+18*np.exp(-((x-45)**2+(y-50)**2)/100)-24*np.exp(-((x-130)**2+(y-50)**2)/100)
    centers=pressure_centers(pressure)
    assert {c[0] for c in centers}=={'H','L'}
    for kind,row,col,value in centers:
        assert row==pytest.approx(50,abs=1)
        assert col==pytest.approx(45 if kind=='H' else 130,abs=1)
        assert value>1030 if kind=='H' else value<995
    pressure[50,130]=np.nan
    assert all(c[0]!='L' for c in pressure_centers(pressure))


def test_pressure_centers_reject_boundary_extrema():
    y,x=np.mgrid[:80,:100]
    pressure=1015-20*np.exp(-((x-3)**2+(y-40)**2)/80)
    assert pressure_centers(pressure)==[]


def test_field_selection_excludes_orography_and_wrong_pressure():
    assert field_key('gh','isobaricInhPa',500,'gfs')=='height500'
    assert field_key('gh','surface',0,'gfs') is None
    assert field_key('mslma','meanSea',0,'hrrr')=='pressure'
    assert field_key('prmsl','meanSea',0,'hrrr') is None
    assert field_key('2t','heightAboveGround',2,'hrrr')=='temperature2'
    assert field_key('2d','heightAboveGround',2,'gfs')=='dewpoint2'
    assert field_key('t','isobaricInhPa',500,'gfs') is None
    assert field_key('u','isobaricInhPa',500,'hrrr')=='u500'
    assert field_key('absv','isobaricInhPa',500,'hrrr')=='vorticity500'
    assert field_key('absv','isobaricInhPa',850,'gfs') is None


def test_scalar_display_units_and_wind_magnitude():
    fields=dict(temperature2=np.array([273.15,233.15]),dewpoint2=np.array([263.15]),
                u500=np.array([3.]),v500=np.array([4.]),vorticity500=np.array([.0002,-.0001]))
    assert scalar_field(fields,'temp2m').tolist()==pytest.approx([32,-40])
    assert scalar_field(fields,'dewpoint2m')[0]==pytest.approx(14)
    assert scalar_field(fields,'wind500')[0]==pytest.approx(9.71922246)
    assert scalar_field(fields,'vort500').tolist()==pytest.approx([20,-10])


def test_new_surface_parameters_use_their_actual_model_fields():
    fields=dict(u10=np.array([6.]),v10=np.array([8.]),humidity2=np.array([73.]),pressure=np.array([100800.]),cape=np.array([1750.]))
    assert scalar_field(fields,'wind10')[0]==pytest.approx(19.4384449244)
    assert scalar_field(fields,'rh2m')[0]==73
    assert scalar_field(fields,'mslp')[0]==1008
    assert scalar_field(fields,'sbcape')[0]==1750
    assert 'precip' not in available_products('nam') and 'sbcape' in available_products('nam')
    assert len(available_products('gfs'))==9 and len(available_products('nam'))==8
    metadata=parameter_metadata()
    for item in metadata:
        if item['id']!='precip':assert len(item['swatches'])==len(item['levels'])-1


def test_nam_cycle_and_native_region_placement():
    from models.render import region_presets
    now=datetime(2026,10,30,7,15,tzinfo=timezone.utc)
    assert candidate_cycles('nam',now)[0].hour==0
    assert len(cycle_plans('nam',now,84,3)[0][1])==29
    grid=dict(type='lambert',earth_radius=6371229,central_lon=-95,central_lat=25,parallel1=25,parallel2=25)
    presets=region_presets(grid);nc=next(p for p in presets if p['id']=='carolinas')
    assert nc['zoom']==4 and 1200<nc['x']<2300 and 500<nc['y']<1200
    assert field_key('prmsl','meanSea',0,'nam')=='pressure'
    assert field_key('cape','surface',0,'nam')=='cape'
    assert field_key('cape','pressureFromGroundLayer',18000,'nam') is None


def test_binary_readouts_preserve_units_and_mask_map_margins(tmp_path):
    import matplotlib.pyplot as plt
    from models.render import write_readouts
    projection=ccrs.PlateCarree();fig=plt.figure(figsize=(16,9))
    ax=fig.add_axes([.05,.1,.9,.8],projection=projection)
    ax.set_extent([-125,-65,25,50],crs=projection)
    x=np.linspace(-130,-60,30);y=np.linspace(20,55,20)
    fields={'temperature2':np.full((20,30),273.15),'dewpoint2':np.full((20,30),263.15)}
    try:spec=write_readouts(tmp_path/'map.png',ax,fields,x,y,projection,projection)
    finally:plt.close(fig)
    values=np.frombuffer((tmp_path/spec['filename']).read_bytes(),dtype='<i2').reshape(2,spec['height'],spec['width'])
    valid=values[0]!=-32768
    assert valid.any() and (~valid).any()
    assert np.all(values[0][valid]==320) and np.all(values[1][valid]==140)


def test_hrrr_range_download_rejects_full_file_responses(tmp_path):
    from models.data import fetch_hrrr_vorticity
    class Reply:
        text='1:0:d=test:ABSV:500 mb:anl:\n2:100:d=test:OTHER:500 mb:anl:\n'
        content=text.encode();status_code=200;headers={}
        def raise_for_status(self):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
    class HTTP:
        def get(self,*args,**kwargs):return Reply()
    with pytest.raises(ValueError,match='byte range'):
        fetch_hrrr_vorticity(HTTP(),tmp_path,datetime(2026,10,30,tzinfo=timezone.utc),0)
    assert not list(tmp_path.glob('*.grib2'))


def test_cycles_cross_midnight_and_obey_publication_delay():
    now=datetime(2026,10,30,2,15,tzinfo=timezone.utc)
    assert candidate_cycles('gfs',now)[0]==datetime(2026,10,29,18,tzinfo=timezone.utc)
    assert candidate_cycles('hrrr',now)[0]==datetime(2026,10,30,0,tzinfo=timezone.utc)
    assert candidate_cycles('hrrr',now)[2].day==29
    assert len(frame_hours(72,3))==25 and len(frame_hours(18,1))==19
    with pytest.raises(ValueError):frame_hours(7,3)


def test_hrrr_native_grid_placement_and_scanning():
    grid=dict(type='lambert',earth_radius=6371229,central_lon=-97.5,central_lat=38.5,
              parallel1=38.5,parallel2=38.5,first_lon=-122.719528,first_lat=21.138123,
              cols=3,rows=2,dx=3000,dy=3000,i_negative=0,j_positive=1)
    projection=projection_for(grid);x,y=native_axes(grid,projection)
    lon,lat=ccrs.PlateCarree().transform_point(x[0],y[0],projection)
    assert lon==pytest.approx(grid['first_lon'],abs=1e-7)
    assert lat==pytest.approx(grid['first_lat'],abs=1e-7)
    assert np.diff(x).tolist()==[3000,3000] and np.diff(y).tolist()==[3000]
    grid.update(i_negative=1,j_positive=0)
    xx,yy=native_axes(grid,projection)
    assert np.diff(xx).tolist()==[-3000,-3000] and np.diff(yy).tolist()==[-3000]


def test_full_horizons_and_extended_hrrr_fallback():
    now=datetime(2026,10,30,7,15,tzinfo=timezone.utc)
    gfs=cycle_plans('gfs',now,384,3)
    assert len(gfs[0][1])==129 and gfs[0][1][-1]==384
    hrrr=cycle_plans('hrrr',now,48,1)
    assert len(hrrr)==6
    assert [cycle.hour for cycle,_ in hrrr[:3]]==[0,18,12]
    assert all(len(hours)==49 and hours[-1]==48 for _,hours in hrrr[:3])
    assert hrrr[3][0].hour==5 and hrrr[3][1][-1]==18
    assert all(cycle.hour%6==0 for cycle,_ in hrrr[:3])
    assert len(cycle_plans('hrrr',now,2,1))==3


def test_failed_generation_preserves_published_manifest(tmp_path,monkeypatch):
    import models.__main__ as command
    output=tmp_path/'generated/models';output.mkdir(parents=True)
    manifest=output/'latest.json';manifest.write_text('previous successful publication')
    monkeypatch.setattr(command,'ROOT',tmp_path)
    monkeypatch.setattr(command,'geography',lambda *args:({},[],[]))
    monkeypatch.setattr(command,'time',SimpleNamespace(sleep=lambda _:None))
    def unavailable(*args):raise RuntimeError('NOAA unavailable')
    monkeypatch.setattr(command,'fetch_frame',unavailable)
    with pytest.raises(RuntimeError,match='Neither model'):
        command.run(SimpleNamespace(gfs_end=0,gfs_step=3,hrrr_end=0,hrrr_step=1))
    assert manifest.read_text()=='previous successful publication'


def test_unavailable_extended_runs_publish_explicit_short_fallback(tmp_path,monkeypatch):
    import models.__main__ as command
    import models.generation as generation
    probes=[]
    monkeypatch.setattr(command,'ROOT',tmp_path)
    monkeypatch.setattr(command,'geography',lambda *args:({},[],[]))
    monkeypatch.setattr(command,'time',SimpleNamespace(sleep=lambda _:None))
    monkeypatch.setattr(command,'region_presets',lambda _:[])
    def fetch(http,cache,model,cycle,hour):
        probes.append((model,cycle.hour,hour))
        if model=='hrrr' and hour>18:raise RuntimeError('Extended run not published')
        return {},{'id':'test-grid'},'https://example.test/source',100
    monkeypatch.setattr(command,'fetch_frame',fetch)
    monkeypatch.setattr(generation,'render',lambda target,*args:target.write_bytes(b'test frame'))
    manifest=command.run(SimpleNamespace(gfs_end=0,gfs_step=3,hrrr_end=48,hrrr_step=1))
    hrrr=next(m for m in manifest['models'] if m['id']=='hrrr')
    assert hrrr['requested_end_hour']==48 and hrrr['forecast_end_hour']==18
    assert hrrr['extended_run'] is False and len(hrrr['frames'])==19
    extended=[p for p in probes if p[0]=='hrrr' and p[2]==48]
    assert len(extended)==3 and all(hour%6==0 for _,hour,_ in extended)
