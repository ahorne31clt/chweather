import numpy as np


def solar_altitude(time,lat,lon):
    # NOAA fractional-year equations; sufficient for masks at 3-hour sampling.
    gamma=2*np.pi/365.2425*(time.timetuple().tm_yday-1+(time.hour+time.minute/60-12)/24)
    equation=229.18*(.000075+.001868*np.cos(gamma)-.032077*np.sin(gamma)-.014615*np.cos(2*gamma)-.040849*np.sin(2*gamma))
    dec=.006918-.399912*np.cos(gamma)+.070257*np.sin(gamma)-.006758*np.cos(2*gamma)+.000907*np.sin(2*gamma)-.002697*np.cos(3*gamma)+.00148*np.sin(3*gamma)
    angle=np.deg2rad(((time.hour*60+time.minute+equation+4*lon)/4-180))
    phi=np.deg2rad(lat)
    return np.rad2deg(np.arcsin(np.clip(np.sin(phi)*np.sin(dec)+np.cos(phi)*np.cos(dec)*np.cos(angle),-1,1)))


def mean_where(values,mask):
    good=mask&np.isfinite(values);count=good.sum(axis=0)
    return np.divide(np.where(good,values,0).sum(axis=0),count,out=np.full(count.shape,np.nan),where=count>0)


def index_score(kind,temp,rh,wind,pop,gust=None):
    if kind=='comfort':
        return np.clip(100-2.5*np.maximum(60-temp,0)-3*np.maximum(temp-78,0)-.5*np.maximum(rh-60,0)-3*np.maximum(wind-8,0)-.8*pop,0,100)
    if kind=='outdoor':
        thermal=np.clip(100-1.7*np.maximum(50-temp,0)-2.2*np.maximum(temp-82,0),0,100)
        return np.clip(thermal-.25*np.maximum(rh-65,0)-2*np.maximum(wind-10,0)-2*np.maximum(gust-20,0)-.8*pop,0,100)
    raise ValueError('Unknown index')


def frost_categories(temp,rh,wind,cloud,night):
    valid=np.isfinite(temp)&np.isfinite(rh)&np.isfinite(wind)&np.isfinite(cloud)&night
    category=np.zeros(temp.shape,dtype=float)
    category[(temp>32)&(temp<=36)&(rh>=80)&(wind<=5)&(cloud<=30)]=1
    category[temp<=32]=2;category[temp<=28]=3
    result=np.max(np.where(valid,category,-1),axis=0)
    return np.where(result<0,np.nan,result)


def accumulate(pieces,start,end):
    cursor=start;total=None
    for a,b,values in sorted(pieces,key=lambda p:p[0]):
        if a!=cursor or b<=a:raise ValueError('Accumulations must be consecutive and non-overlapping')
        total=values.copy() if total is None else total+values;cursor=b
    if cursor!=end or total is None:raise ValueError('Accumulations do not cover the forecast window')
    return total
