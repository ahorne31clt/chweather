import numpy as np
from models.fields import scalar_field,available_products
from models.winter import diagnose_type
from models.__main__ import cycle_plans
from datetime import datetime,timezone

def test_vector_shear_is_not_speed_difference():
    f={'u500':np.array([10.]),'v500':np.array([0.]),'u10':np.array([-10.]),'v10':np.array([0.])}
    assert np.allclose(scalar_field(f,'shear500'),20*1.94384449244)

def test_lcl_estimate_and_cin_units():
    assert np.allclose(scalar_field({'temperature2':np.array([290.]),'dewpoint2':np.array([280.])},'lcl'),1250)
    assert np.allclose(scalar_field({'cin':np.array([-50.])},'cin'),50)

def test_stull_outside_documented_domain_is_missing():
    assert np.isnan(scalar_field({'temperature2':np.array([220.]),'humidity2':np.array([50.])},'wetbulb2m')[0])

def profile(temperatures,surface=-3,reflectivity=20):
    levels=[1000,950,900,850,800,750,700,650,600,550,500]
    f={'temperature2':np.array([[surface+273.15]]),'surface_pressure':np.array([[100000.]]),'reflectivity':np.array([[reflectivity]])}
    for i,p in enumerate(levels):f['temperature'+str(p)]=np.array([[temperatures[i]+273.15]]);f['height'+str(p)]=np.array([[i*500.]])
    return diagnose_type(f,levels)[0,0]

def test_dry_profile_is_not_snow():assert profile([-5]*11,reflectivity=0)==0

def test_cold_and_warm_profiles():
    assert profile([-5]*11)==2
    assert profile([5]*11,surface=5)==1

def test_marginal_profile_remains_uncertain():assert profile([.2]*11,surface=.2)==6

def test_euro_cadence_reaches_full_run_and_cape_is_not_mislabeled():
    plans=cycle_plans('ecmwf',datetime(2026,11,5,18,tzinfo=timezone.utc),360,3)
    assert plans[0][1]==list(range(0,145,3))+list(range(150,361,6))
    assert 'sbcape' not in available_products('ecmwf')
    assert 'mucape' in available_products('ecmwf')
