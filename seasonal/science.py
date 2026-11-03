"""Calendar-aware seasonal aggregates and explicitly historical analog statistics."""
import calendar
from datetime import date
import numpy as np


def add_month(year,month,offset):
    total=year*12+month-1+offset
    return total//12,total%12+1


def months(start,count=3):
    return [add_month(*start,i) for i in range(count)]


def season_name(start,count=3):
    return '-'.join(date(y,m,1).strftime('%b %Y') for y,m in [start,add_month(*start,count-1)])


def seasonal_anomaly(values,start,variable,count=3):
    weights=np.array([calendar.monthrange(y,m)[1] for y,m in months(start,count)])
    if len(values)!=count:raise ValueError('A seasonal anomaly requires every requested month')
    if variable=='temperature':return np.average(values,axis=0,weights=weights)*1.8
    if variable=='precipitation':return np.sum(values*weights[:,None,None],axis=0)/25.4
    raise ValueError('Unsupported seasonal variable')


def probability_fields(arrays):
    data=np.stack(arrays).astype(float)
    valid=np.isfinite(data).all(axis=0)
    if not valid.any():raise ValueError('No valid seasonal probabilities')
    # CPC files currently say percent but encode fractions; validate the simplex,
    # rather than guessing from an isolated small probability.
    total=data.sum(axis=0)
    if np.allclose(total[valid],1,atol=.015):data*=100
    elif not np.allclose(total[valid],100,atol=1.5):raise ValueError('Probability categories do not sum to 100 percent')
    if np.any((data[:,valid]<0)|(data[:,valid]>100.01)):raise ValueError('Invalid probability range')
    return np.where(valid[None,:,:],data,np.nan)


def choose_analogs(rows,now,count=10):
    usable=[r for r in rows if r['anomaly_c'] is not None]
    latest=usable[-1]
    if (now.year*12+now.month)-(latest['year']*12+latest['center_month'])>4:
        raise ValueError('ENSO observation is too old for analog selection')
    phase=lambda v:1 if v>=.5 else -1 if v<=-.5 else 0
    wanted=phase(latest['anomaly_c']);events={};event=0;group=[];last=None
    for r in usable:
        current=(phase(r['anomaly_c']),r['year']*12+r['center_month'])
        if last is None or current[0]!=last[0] or current[1]!=last[1]+1:
            if group and len(group)>=5:
                for key in group:events[key]=event
            event+=1;group=[]
        group.append((r['year'],r['center_month']));last=current
    if len(group)>=5:
        for key in group:events[key]=event
    candidates=[r for r in usable if r['center_month']==latest['center_month'] and r['year']<latest['year']
                and phase(r['anomaly_c'])==wanted and (wanted==0 or (r['year'],r['center_month']) in events)]
    selected=[];seen=set()
    for r in sorted(candidates,key=lambda r:(abs(r['anomaly_c']-latest['anomaly_c']),-r['year'])):
        key=events.get((r['year'],r['center_month']),r['year']) if wanted else r['year']
        if key in seen:continue
        seen.add(key);selected.append(r)
        if len(selected)==count:break
    if len(selected)<8:raise ValueError('Fewer than eight independent ENSO analogs available')
    return latest,selected,{1:'El Nino',-1:'La Nina',0:'Neutral'}[wanted]


def station_statistics(series,start,analog_starts,variable,include_low_snow=False):
    """Require every month, at least 24 normal years and eight analogs."""
    column={'temperature':0,'precipitation':1,'snowfall':2}[variable]
    def aggregate(window):
        values=np.array([series.get((y,m),[np.nan]*3)[column] for y,m in months(window)])
        if not np.isfinite(values).all():return np.nan
        if variable=='temperature':return np.average(values,weights=[calendar.monthrange(y,m)[1] for y,m in months(window)])
        return values.sum()
    # Normal years refer to the center month (e.g. DJF 1991 = Dec 1990-Feb 1991).
    shift=add_month(*start,1)[0]-start[0]
    normal=np.array([aggregate((year-shift,start[1])) for year in range(1991,2021)])
    analog=np.array([aggregate(window) for window in analog_starts])
    normal=normal[np.isfinite(normal)];analog=analog[np.isfinite(analog)]
    if len(normal)<24 or len(analog)<8:return None
    mean=float(normal.mean())
    if variable=='snowfall' and mean<1 and not include_low_snow:return None
    return dict(normal=mean,anomaly=float(analog.mean()-mean),above=float((analog>mean).mean()*100),
                below=float((analog<mean).mean()*100),equal=float((analog==mean).mean()*100),
                normal_years=len(normal),analog_count=len(analog),analog_values=analog.tolist())
