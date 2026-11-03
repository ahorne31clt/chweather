import numpy as np
from optics.contrails import saturation_ice,saturation_water,layer,diagnose,EPSILON,LEVELS


def humidity(t,p,rhi):
    vapor=rhi*saturation_ice(t)
    return EPSILON*vapor/(p-(1-EPSILON)*vapor)


def test_saturation_reference_and_ice_water_distinction():
    assert abs(saturation_water(273.15)-611.2)<1
    assert abs(saturation_ice(273.15)-611.2)<1
    assert saturation_ice(220)<saturation_water(220)


def test_cold_supersaturated_layer_can_support_persistent_contrail():
    category,rhi=layer(np.array([220.]),humidity(220.,25000.,1.1),25000.)
    assert category[0]==2 and np.isclose(rhi[0],1.1)


def test_formation_and_persistence_are_separate():
    category,_=layer(np.array([210.]),humidity(210.,25000.,.5),25000.)
    assert category[0]==1
    warm,_=layer(np.array([250.]),humidity(250.,25000.,1.1),25000.)
    assert warm[0]==0


def test_no_high_cloud_or_daylight_required_and_pressure_is_reported():
    fields={}
    for p in LEVELS:
        fields['temp'+str(p)]=np.array([[220.]])
        fields['q'+str(p)]=np.array([[humidity(220.,p*100.,1.2 if p==250 else .5)]])
    result=diagnose(fields)
    assert result['category'][0,0]==2
    assert result['pressure_hpa'][0,0]==250
    assert np.isclose(result['rhi'][0,0],1.2)


def test_zero_moisture_never_gets_persistence_flag():
    category,rhi=layer(np.array([210.,220.,250.]),np.zeros(3),25000.)
    assert np.all(category<2) and np.all(rhi==0)


def test_clear_night_still_reports_contrail_environment():
    from datetime import datetime,timezone
    from optics.science import score
    lat=np.arange(30.,42.);lon=np.arange(-90.,-70.)
    shape=(len(lat),len(lon));constant=lambda x:np.full(shape,x)
    fields={k:constant(v) for k,v in dict(low=0,middle=0,high=0,visibility=20000,rate=0,rain=0).items()}
    for p in (200,250,300,350,400,500):
        fields['temp'+str(p)]=constant(220.)
        if p in LEVELS:fields['q'+str(p)]=constant(humidity(220.,p*100.,1.1))
        if p in (300,400,500):fields.update({f'rh{p}':constant(40.),f'ice{p}':constant(0.)})
    result,alt=score(fields,datetime(2026,11,3,5,tzinfo=timezone.utc),lat,lon)
    assert np.all(alt<0)
    assert np.all(result['halo']==0)
    assert np.all(result['contrail']==2)
