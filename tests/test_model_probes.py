import numpy as np
import pytest
from models.readouts import values_for_grid


def test_all_map_quantities_are_exported_in_display_units():
    array=lambda n:np.full((2,3),n,dtype=float)
    fields=dict(temperature2=array(273.15),dewpoint2=array(263.15),u10=array(3),v10=array(4),u500=array(30),v500=array(40),
        humidity2=array(80),pressure=array(101300),height500=array(5600),height1000=array(160),
        vorticity500=array(.0002),cape=array(1234),rate=array(1/3600),rain=array(1),snow=array(0),freezing_rain=array(0),sleet=array(0))
    result={spec['id']:values for spec,values in values_for_grid(fields)}
    assert result['temperature2'][0,0]==pytest.approx(32)
    assert result['wind10'][0,0]==pytest.approx(9.71922246)
    assert result['height500'][0,0]==560 and result['pressure'][0,0]==1013
    assert result['vorticity500'][0,0]==pytest.approx(20)
    assert result['rate'][0,0]==1 and result['precip_type'][0,0]==1
    assert result['thickness'][0,0]==544 and result['cape'][0,0]==1234
    fields['rain'][0,0]=np.nan
    missing={spec['id']:values for spec,values in values_for_grid(fields)}
    assert np.isnan(missing['precip_type'][0,0])
