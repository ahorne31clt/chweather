"""Compact shared raw-value grids for map probes and display-only smoothing."""
from pathlib import Path
import gzip
import numpy as np
from scipy.ndimage import gaussian_filter
from .fields import scalar_field
from .product import classify


def values_for_grid(fields,model=None):
    entries=[]
    for key,product,unit,digits in [('temperature2','temp2m','°F',1),('dewpoint2','dewpoint2m','°F',1),
        ('wind10','wind10','kt',1),('humidity2','rh2m','%',1),('pressure','mslp','hPa',1),
        ('wind500','wind500','kt',1),('vorticity500','vort500','10⁻⁵ s⁻¹',1),('cape','sbcape','J/kg',0)]:
        if product=='wind10' and 'u10' not in fields:continue
        if product=='wind500' and 'u500' not in fields:continue
        if key in ('humidity2','pressure','vorticity500','cape','temperature2','dewpoint2') and key not in fields:continue
        entries.append((dict(id=key,unit=unit,decimals=digits),scalar_field(fields,product)))
    if 'height500' in fields:entries.append((dict(id='height500',unit='dam',decimals=1),fields['height500']/10))
    if {'height500','height1000'}<=set(fields):entries.append((dict(id='thickness',unit='dam',decimals=1),(fields['height500']-fields['height1000'])/10))
    if {'rain','snow','freezing_rain','sleet','rate'}<=set(fields):
        kind,rate,_=classify(fields)
        known=np.isfinite(fields['rate'])&np.logical_and.reduce([np.isfinite(fields[key]) for key in ('rain','snow','freezing_rain','sleet')])
        entries.extend([(dict(id='rate',unit='mm/hr',decimals=2),rate),(dict(id='precip_type',unit='',decimals=0),np.where(known,kind,np.nan))])
    if 'vorticity500' in fields:
        sigma=5 if fields['vorticity500'].shape[1]>1000 else 1
        entries.append((dict(id='display_vorticity500',unit='10⁻⁵ s⁻¹',decimals=1),gaussian_filter(fields['vorticity500']*100000,sigma=sigma)))
    return entries


def write_grid(path,ax,fields,x,y,source_crs,projection,sampler):
    ax.apply_aspect();left,bottom,width,height=ax.get_position().bounds
    xx,yy=np.meshgrid(np.arange(2,2400,4),np.arange(2,1350,4))
    xmin,xmax=ax.get_xlim();ymin,ymax=ax.get_ylim()
    fx=(xx/2400-left)/width;fy=(1-yy/1350-bottom)/height
    inside=(fx>=0)&(fx<=1)&(fy>=0)&(fy<=1);specs=[];arrays=[]
    for spec,values in values_for_grid(fields):
        sampled=sampler(values,x,y,source_crs,projection,xmin+fx*(xmax-xmin),ymin+fy*(ymax-ymin))
        sampled[~inside]=np.nan
        finite=np.isfinite(sampled);encoded=np.full(sampled.shape,-2147483648,dtype='<i4')
        quantized=np.rint(sampled[finite]*10**spec['decimals'])
        if np.any(np.abs(quantized)>=2147483647):raise ValueError('Probe values exceed lossless display encoding')
        encoded[finite]=quantized.astype('<i4');arrays.append(encoded);specs.append(spec)
    target=Path(path).with_name(Path(path).stem.removesuffix('-temp2m')+'.bin.gz')
    values=np.stack(arrays);delta=values.copy();delta[:,:,1:]=values[:,:,1:]-values[:,:,:-1]
    target.write_bytes(gzip.compress(delta.tobytes(),compresslevel=6,mtime=0))
    return dict(filename=target.name,width=xx.shape[1],height=xx.shape[0],cell_pixels=4,
        dtype='int32-le',delta_axis='x',missing=-2147483648,encoding='gzip',field_specs=specs,fields=[s['id'] for s in specs],
        map_box_pixels=[left*2400,(1-bottom-height)*1350,width*2400,height*1350],
        method='Nearest native model samples; rounded to documented display precision. Smoothing never changes probe values.')
