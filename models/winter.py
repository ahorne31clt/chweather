"""Conservative experimental dry-bulb profile diagnosis, not native model flags."""
import numpy as np
from .product import TYPE_COLORS

def diagnose_type(fields,levels):
    t=np.stack([fields['temperature'+str(p)]-273.15 for p in levels])
    z=np.stack([fields['height'+str(p)] for p in levels])
    pressure=np.asarray(levels)[:,None,None]*100
    above=pressure<=fields['surface_pressure'][None,:,:]
    valid=above&np.isfinite(t)&np.isfinite(z)
    first=np.argmax(valid,axis=0)
    t0=np.take_along_axis(t,first[None],axis=0)[0]+273.15
    z0=np.take_along_axis(z,first[None],axis=0)[0]
    p0=np.take_along_axis(np.broadcast_to(pressure,t.shape),first[None],axis=0)[0]
    surface_z=z0-29.3*t0*np.log(fields['surface_pressure']/p0)
    surface_t=fields['temperature2']-273.15
    warm=valid&(t>=2)
    bottom=np.min(np.where(warm,z,np.inf),axis=0)
    top=np.max(np.where(warm,z,-np.inf),axis=0)
    warm_depth=np.where(np.isfinite(bottom),top-bottom,0)
    cold_depth=bottom-surface_z
    maximum=np.maximum(np.max(np.where(valid,t,-np.inf),axis=0),surface_t)
    minimum_cold=np.min(np.where(valid&(z<bottom[None]),t,np.inf),axis=0)
    wet=np.isfinite(fields['reflectivity'])&(fields['reflectivity']>=5)
    complete=valid.sum(axis=0)>=10
    result=np.where(wet,6,0).astype('uint8')
    result[wet&complete&(maximum<=-.5)]=2
    result[wet&complete&(surface_t>=3)]=1
    melted=wet&complete&(warm_depth>=500)&(surface_t<=-.5)
    result[melted&(cold_depth>=0)&(cold_depth<500)]=3
    result[melted&(cold_depth>1200)&(minimum_cold<=-4)]=4
    return result

def profile_colors(fields):
    kind=fields['diagnosed_type'];rgba=np.zeros((*kind.shape,4),dtype=np.float32)
    for index,color in enumerate(TYPE_COLORS[1:],1):
        mask=kind==index;rgba[mask,:3]=[int(color[i:i+2],16)/255 for i in (1,3,5)];rgba[mask,3]=.9
    return kind,rgba
