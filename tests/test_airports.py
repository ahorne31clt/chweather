import numpy as np
import pytest

from models.airports import airport_values,nearest_indices,airport_indices


def test_nearest_axis_sampling_and_outside_grid():
    index,valid=nearest_indices(np.array([0.,10.,20.]),np.array([1.,9.,21.]))
    assert index.tolist()==[0,1,2] and valid.tolist()==[True,True,False]
    index,valid=nearest_indices(np.array([20.,10.,0.]),np.array([1.,9.,21.]))
    assert index.tolist()==[2,1,0] and valid.tolist()==[True,True,False]


def test_airport_units_use_surface_wind_and_instantaneous_rate():
    fields=dict(temperature2=np.array([[273.15,280.]]),rate=np.array([[1/3600,0.]]))
    wind=dict(u10=np.array([[3.,4.]]),v10=np.array([[4.,0.]]))
    result=airport_values(fields,wind,(np.array([0,0]),np.array([0,1]),np.array([True,False])))
    assert result[0].tolist()==pytest.approx([32,9.71922246,1])
    assert np.isnan(result[1]).all()


def test_airport_samples_are_nearest_native_grid_points():
    grid=dict(type='regular_ll',longitudes=np.array([-81.,-80.]),latitudes=np.array([35.,36.]))
    airports=[dict(lon=-80.94,lat=35.21),dict(lon=-79.,lat=35.2)]
    rows,cols,valid=airport_indices(grid,airports)
    assert rows.tolist()==[0,0] and cols.tolist()==[0,1] and valid.tolist()==[True,False]
