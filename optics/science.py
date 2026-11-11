"""Transparent ingredient heuristics, never calibrated event probabilities."""
import numpy as np
from scipy.ndimage import map_coordinates
from specialty.science import solar_altitude

PHENOMENA={
 'contrail':('Persistent contrail environment','If a suitable aircraft crosses a qualifying cold, ice-supersaturated layer, its contrail could persist and spread into cirrus. This does not predict flights, cloud lifetime, halos or sundogs.'),
 'halo':('22-degree halo','Thin high ice cloud with the Sun visible; random crystal orientations can form a ring.'),
 'sundog':('Sundogs','Plate crystals preferentially oriented horizontally; strongest viewing usually with a low Sun.'),
 'zenithal':('Circumzenithal arc','Horizontally oriented plate crystals; Sun must be below approximately 32 degrees.'),
 'horizontal':('Circumhorizontal arc','Horizontally oriented plate crystals; Sun must exceed approximately 58 degrees.'),
 'tangent':('Upper tangent arc','Horizontally oriented column crystals; shape changes with solar elevation.'),
 'rainbow':('Rainbow','Liquid rain opposite the Sun, an illuminated viewing path, and solar elevation below about 42 degrees for a ground observer.')}


def geometry(time,lat,lon):
    altitude=solar_altitude(time,lat,lon)
    gamma=2*np.pi/365.2425*(time.timetuple().tm_yday-1+(time.hour+time.minute/60-12)/24)
    eq=229.18*(.000075+.001868*np.cos(gamma)-.032077*np.sin(gamma)-.014615*np.cos(2*gamma)-.040849*np.sin(2*gamma))
    dec=.006918-.399912*np.cos(gamma)+.070257*np.sin(gamma)-.006758*np.cos(2*gamma)+.000907*np.sin(2*gamma)-.002697*np.cos(3*gamma)+.00148*np.sin(3*gamma)
    hour=np.deg2rad((time.hour*60+time.minute+eq+4*lon)/4-180)
    phi=np.deg2rad(lat)
    east=-np.cos(dec)*np.sin(hour)
    north=np.cos(phi)*np.sin(dec)-np.sin(phi)*np.cos(dec)*np.cos(hour)
    return altitude,np.arctan2(east,north)


def sample(field,lat,lon,azimuth,distance):
    """Approximate short horizontal viewing rays on a regular lat/lon grid."""
    yy,xx=np.meshgrid(lat,lon,indexing='ij')
    target_lat=yy+distance*np.cos(azimuth)/111.2
    target_lon=xx+distance*np.sin(azimuth)/(111.2*np.cos(np.deg2rad(yy)))
    return map_coordinates(field,[(target_lat-lat[0])/(lat[1]-lat[0]),(target_lon-lon[0])/(lon[1]-lon[0])],order=1,mode='constant',cval=np.nan)


def score(fields,time,lat,lon,contrail=None):
    xx,yy=np.meshgrid(lon,lat);alt,az=geometry(time,yy,xx)
    low=np.clip(fields['low']/100,0,1);middle=np.clip(fields['middle']/100,0,1);high=np.clip(fields['high']/100,0,1)
    # RH is the model's published RH, not a derived ice-supersaturation diagnosis.
    cold=np.stack([np.clip((263.15-fields['temp'+str(p)])/20,0,1) for p in (300,400,500)])
    humidity=np.stack([np.clip((fields['rh'+str(p)]-50)/40,0,1) for p in (300,400,500)])
    ice=np.stack([1-np.exp(-np.maximum(fields['ice'+str(p)],0)/1e-5) for p in (300,400,500)])
    crystal_environment=np.max(cold*(.4*humidity+.6*ice),axis=0)
    # Estimate a sunward sightline using representative cloud heights.
    slope=np.maximum(np.tan(np.deg2rad(np.clip(alt,1,89))),.02)
    low_path=sample(low,lat,lon,az,np.clip(1.5/slope,2,75))
    mid_path=sample(middle,lat,lon,az,np.clip(4/slope,2,75))
    local_clear=(1-low)*(1-.8*middle)
    sun_clear=(1-low_path)*(1-.8*mid_path)
    visible=np.clip(fields['visibility']/15000,0,1)*np.sqrt(np.maximum(0,local_clear*sun_clear))
    veil=np.sqrt(high)*(1-.55*high**3)
    local_ice=veil*crystal_environment
    sunward_ice=sample(local_ice,lat,lon,az,np.clip(8/slope,2,75))
    base=100*(.55*local_ice+.45*sunward_ice)*visible
    daylight=alt>0
    result={'halo':np.where(daylight,base,0),
      'sundog':np.where(daylight,base*(.25+.75*np.exp(-((alt-12)/25)**2)),0),
      'zenithal':np.where(daylight&(alt<32),base*np.exp(-((alt-22)/14)**2),0),
      'horizontal':np.where(alt>58,base*np.exp(-((alt-68)/18)**2),0),
      'tangent':np.where(daylight,base,0)}
    rain=np.maximum(fields['rate'],0)*3600*np.clip(fields['rain'],0,1)
    wet=[sample(rain,lat,lon,az+np.pi+angle,d) for d in (10,25,40) for angle in (-.35,0,.35)]
    drops=np.max(np.stack(wet),axis=0)
    result['rainbow']=np.where(daylight&(alt<42),100*(1-np.exp(-drops/.5))*visible,0)
    if 'q200' in fields:
        from .contrails import diagnose
        result['contrail']=(contrail if contrail is not None else diagnose(fields))['category']
    return {k:np.clip(v,0,100) for k,v in result.items()},alt
