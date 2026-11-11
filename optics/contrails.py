"""Conditional contrail environment, not aircraft or halo occurrence odds."""
from functools import lru_cache
import numpy as np
from scipy.optimize import brentq

LEVELS=(150,200,250,300,350,400)
HRRR_LEVELS=tuple(range(200,401,25))
NEAR_SATURATION=.90
EPSILON=.622


def saturation_ice(t):
    """Murphy & Koop (2005) saturation vapor pressure, Pa."""
    return np.exp(9.550426-5723.265/t+3.53068*np.log(t)-.00728332*t)


def saturation_water(t):
    return np.exp(54.842763-6763.22/t-4.210*np.log(t)+.000367*t+
        np.tanh(.0415*(t-218.8))*(53.878-1331.22/t-9.44523*np.log(t)+.014025*t))


@lru_cache(maxsize=20)
def mixing_tangent(pressure_pa,efficiency=.35):
    slope=1.25*1004*pressure_pa/(EPSILON*43e6*(1-efficiency))
    derivative=lambda t:(saturation_water(t+.001)-saturation_water(t-.001))/.002-slope
    tangent=brentq(derivative,190.,273.15)
    return slope,tangent,float(saturation_water(tangent))


def layer(temperature,specific_humidity,pressure_pa):
    vapor=specific_humidity*pressure_pa/(EPSILON+(1-EPSILON)*specific_humidity)
    rhi=vapor/saturation_ice(temperature)
    slope,tangent,water=mixing_tangent(pressure_pa)
    forms=(temperature<tangent)&(vapor+slope*(tangent-temperature)>=water)
    # Ambient ice supersaturation is necessary for the persistence flag.
    category=np.where(forms,np.where(rhi>=1.,2.,1.),0.)
    return category,rhi


def diagnose(fields, levels=LEVELS):
    categories=[];humidities=[]
    for p in levels:
        category,rhi=layer(fields['temp'+str(p)],fields['q'+str(p)],p*100.)
        category=np.where(category==2,3,np.where((category==1)&(rhi>=NEAR_SATURATION),2,category))
        categories.append(category);humidities.append(rhi)
    categories=np.stack(categories);humidities=np.stack(humidities)
    # Prefer the highest category, then its moistest qualifying sampled level.
    category=np.max(categories,axis=0)
    ranking=np.where(categories==category[None,...],humidities,-np.inf)
    chosen=np.argmax(ranking,axis=0)
    select=lambda a:np.take_along_axis(a,chosen[None,...],axis=0)[0]
    pressure=np.array(levels)[chosen]
    return dict(category=category,rhi=select(humidities),pressure_hpa=pressure,
        temperature_c=select(np.stack([fields['temp'+str(p)]-273.15 for p in levels])))


def combined(gfs, hrrr=None):
    if hrrr is None:
        return dict(gfs, hrrr_selected=np.zeros_like(gfs['category']))
    usable=np.isfinite(hrrr['rhi'])
    use_hrrr=usable & (hrrr['category']>=gfs['category'])
    result={key:np.where(use_hrrr,hrrr[key],value) for key,value in gfs.items()}
    return dict(result,hrrr_selected=use_hrrr)
