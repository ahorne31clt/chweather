import numpy as np
from scipy.ndimage import gaussian_filter,maximum_filter,minimum_filter

TYPE_NAMES=['Dry / below threshold','Rain','Snow','Freezing rain','Sleet','Mixed flags','Unclassified precip.']
TYPE_COLORS=['#18191A','#419E68','#72B6DD','#DA6C9D','#B28ED2','#D0AD60','#ADB9B2']
MIN_RATE_MM_HR=.1


def classify(fields):
    """Use the model's flags, never a thickness-derived rain/snow threshold."""
    rate=fields['rate']*3600.0
    flags=np.stack([fields[key] for key in ['rain','snow','freezing_rain','sleet']])
    known=np.isfinite(rate)&np.isfinite(flags).all(axis=0)
    wet=known&(rate>=MIN_RATE_MM_HR)
    active=flags>=.5
    count=active.sum(axis=0)
    kind=np.zeros(rate.shape,dtype=np.uint8)
    for index in range(4):kind[wet&(count==1)&active[index]]=index+1
    kind[wet&(count>1)]=5
    kind[wet&(count==0)]=6
    rgba=np.zeros((*rate.shape,4),dtype=np.float32)
    # Six liquid-equivalent instantaneous-rate bands, brighter for higher rates.
    bands=np.digitize(rate,[.5,2,5,10,20])
    intensity=np.choose(bands,[.45,.56,.67,.78,.9,1.0])
    for index,color in enumerate(TYPE_COLORS[1:],1):
        base=np.array([int(color[i:i+2],16)/255 for i in (1,3,5)])
        mask=kind==index
        rgba[mask,:3]=base*intensity[mask,None]
        rgba[mask,3]=.96
    return kind,rate,rgba


def diagnostics(fields):
    return fields['pressure']/100.0,(fields['height500']-fields['height1000'])/10.0


def pressure_centers(pressure,spacing_km=35):
    """Find broad, closed extrema on a uniform projected grid (hPa).

    Require a 0.75-hPa change all around a 280–350 km ring, rather than
    labeling every noisy local extremum or an open pressure gradient.
    Returns kind, row, column, smoothed pressure; never invents a center.
    """
    valid=np.isfinite(pressure)
    if not valid.any():return []
    sigma=75/spacing_km
    weight=gaussian_filter(valid.astype(float),sigma,mode='constant',cval=0)
    smooth=gaussian_filter(np.where(valid,pressure,0),sigma,mode='constant',cval=0)/np.maximum(weight,1e-9)
    radius=int(np.ceil(350/spacing_km))
    yy,xx=np.mgrid[-radius:radius+1,-radius:radius+1]
    distance=np.hypot(xx,yy)*spacing_km
    disk=distance<=250
    ring=(distance>=280)&(distance<=350)
    interior=minimum_filter(valid.astype(np.uint8),footprint=distance<=350,mode='constant',cval=0).astype(bool)
    confident=interior&(weight>.999)
    candidates=[]
    for kind,sign in [('H',1),('L',-1)]:
        signed=sign*smooth
        peak=maximum_filter(signed,footprint=disk,mode='constant',cval=np.inf)
        ring_max=maximum_filter(signed,footprint=ring,mode='constant',cval=np.inf)
        strength=signed-ring_max
        rows,cols=np.where(confident&(signed==peak)&(strength>=.75))
        candidates.extend((float(strength[row,col]),kind,int(row),int(col),float(smooth[row,col])) for row,col in zip(rows,cols))
    selected=[]
    for _,kind,row,col,value in sorted(candidates,reverse=True):
        if sum(center[0]==kind for center in selected)>=5:continue
        if any(np.hypot(row-r,col-c)*spacing_km<600 for _,r,c,_ in selected):continue
        selected.append((kind,row,col,value))
    return selected
