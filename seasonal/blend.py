"""Experimental, auditable model/statistical seasonal blend.

Development diagnostics are not independent forecast verification. Snow is a
conditional distribution of measured historical snowfall, not a snow-ratio rule.
"""
import numpy as np
from .science import add_month,months,seasonal_anomaly
from . import verification as verify

MODELS=('CFSv2','CanESM5','GEM5.2_NEMO','NASA_GEOS5v2','NCAR_CCSM4','NCAR_CESM1')
SNOW_BANDS=[0,3,6,12,24,36,60,90,120,180,300]
SNOW_LABELS=['0-3','3-6','6-12','12-24','24-36','36-60','60-90','90-120','120-180','180+']


def aggregate(series,start,count=3):
    rows=np.array([series.get(m,[np.nan]*3) for m in months(start,count)])
    import calendar
    weights=[calendar.monthrange(y,m)[1] for y,m in months(start,count)]
    return np.array([np.average(rows[:,0],weights=weights),rows[:,1].sum(),rows[:,2].sum()])


def references(station,start,count=3):
    shift=add_month(*start,count//2)[0]-start[0]
    samples=np.array([aggregate(station['series'],(y-shift,start[1]),count) for y in range(1991,2021)])
    count=np.isfinite(samples).sum(axis=0)
    finite=[col[np.isfinite(col)] for col in samples.T]
    mean=np.array([np.mean(col) if len(col) else np.nan for col in finite]);scale=np.array([np.std(col,ddof=1) if len(col)>1 else np.nan for col in finite])
    scale=np.maximum(scale,[1.,.5,1.])
    return mean,scale,count,samples


def state_features(station,year,init_month,oni,indices,oni_lag,index_lag,lead,duration_months=3):
    anchor=add_month(year,init_month,-oni_lag)
    onival=oni.get(anchor,np.nan);prior=oni.get(add_month(*anchor,-3),np.nan)
    index_month=add_month(year,init_month,-index_lag)
    tele=[indices[k].get(index_month,np.nan) for k in ['ao','nao','pna']]
    recent_start=add_month(year,init_month,-3);recent=aggregate(station['series'],recent_start)
    cached=station.setdefault('_recent_references',{})
    if init_month not in cached:
        normals=np.array([aggregate(station['series'],add_month(y,init_month,-3)) for y in range(1991,2021)])
        finite=[col[np.isfinite(col)] for col in normals[:,:2].T]
        cached[init_month]=(np.array([np.mean(col) if len(col) else np.nan for col in finite]),np.maximum([np.std(col) if len(col)>1 else np.nan for col in finite],[1.,.5]))
    mean,sd=cached[init_month]
    recent=(recent[:2]-mean)/sd
    extras=[indices.get(k,{}).get(index_month,np.nan) for k in ['pdo','qbo','enso_flavor']]
    enso=indices.get('model_enso',{}).get(year,{})
    target_months=months(add_month(year,init_month,lead),duration_months)
    forecast=[v for date,v in zip(enso.get('dates',[]),enso.get('anomaly_c',[])) if date in target_months]
    extras.append(float(np.mean(forecast)) if forecast else np.nan)
    return np.array([onival,onival-prior,*tele,*recent,*extras],dtype=float)


def analog_weights(x,query,lead,k=15,variant='base'):
    columns=np.arange(min(7,x.shape[1])) if 'extended' not in variant else np.arange(x.shape[1])
    valid=np.isfinite(query[columns])
    columns=columns[valid]
    if len(columns)<7:raise ValueError('Core analog predictors missing')
    complete=np.isfinite(x[:,columns]).all(axis=1)
    if complete.sum()<20 and 'extended' in variant:return analog_weights(x,query,lead,k,'base')
    if not complete.any():raise ValueError('No complete analog predictors')
    selected=x[complete][:,columns];spread=np.maximum(np.std(selected,axis=0),.2)
    all_weights=np.array([1.,.5,*([np.exp(-max(lead,0)/3)]*3),.5,.5,.5,.5,.5,.75])[:x.shape[1]]
    distance=np.mean(((selected-query[columns])/spread)**2*all_weights[columns],axis=1)
    chosen=np.argsort(distance)[:min(k,len(selected))]
    result=np.zeros(len(x));indices=np.where(complete)[0][chosen]
    result[indices]=1/(.25+distance[chosen])
    return result/result.sum()


def trend_slope(years,values):
    valid=np.isfinite(values);years=np.asarray(years)[valid];values=np.asarray(values)[valid]
    if len(years)<20:return 0.
    recent=years>=years.max()-39
    slope=float(np.polyfit(years[recent]-years[recent].mean(),values[recent],1)[0])
    return float(np.clip(slope,-.2,.2))*len(years[recent])/(len(years[recent])+20)


def statistical_predictions(x,y,years,query,year,column,lead,normal):
    result={}
    for variant in verify.VARIANTS:
        weights=analog_weights(x,query,lead,variant=variant)
        target=y[:,column].copy()
        if 'trend' in variant and column==0:
            target+=trend_slope(years,target)*np.clip(year-years,0,40)
        result[variant]=float(weights@target)-normal
    return result


def choose_model_weight(rows):
    """Shrink a small-sample development fit toward an even stream blend."""
    if len(rows)<50:raise ValueError('Too few forward-held-out station forecasts for blend weighting')
    values=np.array(rows);actual,model,stat,scale=values.T
    candidates=np.linspace(0,1,21)
    loss=[np.mean(((a*model+(1-a)*stat-actual)/scale)**2)+.025*(a-.5)**2 for a in candidates]
    alpha=float(candidates[int(np.argmin(loss))]);residual=(actual-(alpha*model+(1-alpha)*stat))/scale
    return alpha,residual,dict(model_weight=alpha,statistical_weight=1-alpha,development_cases=len(rows),
        normalized_rmse=float(np.sqrt(np.mean(residual**2))),
        normal_reference_rmse=float(np.sqrt(np.mean((actual/scale)**2))),
        warning='Forward-held-out development cases used to choose weights; not an independent validation set. Stations are spatially correlated.')


def nearest_model(d,station,start,variable,count=3):
    import calendar
    y=int(np.argmin(abs(d['lat']-station['lat'])));x=int(np.argmin(abs(d['lon']-station['lon'])))
    values=[];days=[];column=0 if variable=='temperature' else 1
    for year,month in months(start,count):
        length=calendar.monthrange(year,month)[1];days.append(length)
        if (year,month) in d['dates']:
            value=float(d['values']['fcst'][d['dates'].index((year,month)),y,x])
            values.append(value*1.8 if variable=='temperature' else value*length/25.4)
        elif (year,month)<d['dates'][0]:
            actual=station['series'].get((year,month),[np.nan]*3)[column]
            reference=[station['series'].get((yy,month),[np.nan]*3)[column] for yy in range(1991,2021)]
            reference=np.array(reference);reference=reference[np.isfinite(reference)]
            if len(reference)<24:return np.nan
            values.append(actual-float(reference.mean()))
        else:raise ValueError('Model does not reach the end of the requested snow season')
    return float(np.average(values,weights=days) if variable=='temperature' else np.sum(values))


def weighted_quantile(values,weights,q):
    order=np.argsort(values);v=np.asarray(values)[order];w=np.asarray(weights)[order]
    return float(np.interp(q,np.cumsum(w)/np.sum(w),v))


def calculate(stations,start,init,current,history,oni_rows,indices,duration_months=3):
    oni={(r['year'],r['center_month']):r['anomaly_c'] for r in oni_rows if r['anomaly_c'] is not None}
    latest=max(k for k in oni if k<(init[0],init[1]))
    oni_lag=max(1,(init[0]-latest[0])*12+init[1]-latest[1])
    latest_index=min(max(k for k in values if k<(init[0],init[1])) for values in [indices[k] for k in ['ao','nao','pna']])
    index_lag=max(1,(init[0]-latest_index[0])*12+init[1]-latest_index[1])
    lead=(start[0]-init[0])*12+start[1]-init[1]
    live=[]
    for station in stations:
        f=state_features(station,init[0],init[1],oni,indices,oni_lag,index_lag,lead,duration_months)
        if np.isfinite(f[:7]).all():live.append((station['lon']*.8,station['lat'],f[5:7]))
    if len(live)<30:raise ValueError('Too few recent observed climate records')
    prepared=[];validation={v:[] for v in ['temperature','precipitation']}
    for station in stations:
        normal,scale,counts,samples=references(station,start,duration_months)
        if min(counts[:2])<24:continue
        x=[];y=[];years=[]
        for year in range(1953,init[0]):
            past_start=add_month(year,init[1],lead)
            target=aggregate(station['series'],past_start,duration_months)
            feature=state_features(station,year,init[1],oni,indices,oni_lag,index_lag,lead,duration_months)
            if not np.isfinite(feature[:7]).all() or not np.isfinite(target[:2]).all():continue
            x.append(feature);y.append(target);years.append(year)
        if len(years)<30:continue
        x=np.array(x);y=np.array(y);years=np.array(years)
        query=state_features(station,init[0],init[1],oni,indices,oni_lag,index_lag,lead,duration_months)
        imputed=False
        if not np.isfinite(query[5:7]).all():
            distance=np.array([(x-station['lon']*.8)**2+(y-station['lat'])**2 for x,y,_ in live])
            near=np.argsort(distance)[:4];w=1/np.maximum(distance[near],.01);w/=w.sum()
            query[5:7]=np.sum(np.array([live[i][2] for i in near])*w[:,None],axis=0);imputed=True
        if not np.isfinite(query[:7]).all():continue
        model_hist={};current_model={};raw_models={};bias_terms={}
        for column,variable in enumerate(['temperature','precipitation']):
            model_hist[variable]={}
            for year,data in history.items():
                if year not in years:continue
                value=nearest_model(data[variable],station,add_month(year,init[1],lead),variable,duration_months)
                if np.isfinite(value):model_hist[variable][year]=value
            for year in sorted(model_hist[variable]):
                past=years<year
                if past.sum()<20:continue
                stats=statistical_predictions(x[past],y[past],years[past],x[years==year][0],year,column,lead,normal[column])
                observed=float(y[years==year,column][0])-normal[column]
                validation[variable].append(dict(id=station['id'],region=verify.region(station),year=year,actual=observed,model=model_hist[variable][year],stats=stats,scale=float(scale[column]),climo_probability=float(np.mean(y[past,column]>normal[column]))))
            # Published model anomalies already use their own hindcast reference.
            # Do not impose a recent station offset across changing model versions.
            bias=0.
            components=[nearest_model(current[m,variable],station,start,variable,duration_months) for m in MODELS]
            if not np.isfinite(components).all():break
            raw_models[variable]=float(np.mean(components));bias_terms[variable]=float(np.clip(bias,-2*scale[column],2*scale[column]))
            current_model[variable]=raw_models[variable]+bias_terms[variable]
        if len(current_model)!=2:continue
        weights=analog_weights(x,query,lead)
        prepared.append(dict(station=station,normal=normal,scale=scale,counts=counts,samples=samples,
            x=x,y=y,years=years,query=query,state_weights=weights,model=current_model,raw_models=raw_models,bias_terms=bias_terms,recent_imputed=imputed))
    evaluated={v:verify.evaluate(cases) for v,cases in validation.items()}
    diagnostics={v:dict(model_weight=verify.fit(validation[v])['alpha'],statistical_weight=1-verify.fit(validation[v])['alpha'],
                        development_cases=len(validation[v]),verification=evaluated[v]['report']) for v in validation}
    snow_cases=[]
    for entry in prepared:
        station=entry['station']; y=entry['y']; years=entry['years']; scale=entry['scale']
        if entry['counts'][2]<24:continue
        for year in sorted(history):
            predictions=[evaluated[v]['by_case'].get((station['id'],year)) for v in ('temperature','precipitation')]
            if any(p is None for p in predictions) or year not in years:continue
            past=(years<year)&np.isfinite(y).all(axis=1)
            if past.sum()<24:continue
            actual=float(y[years==year,2][0])
            if not np.isfinite(actual):continue
            samples=y[past]; query=entry['x'][years==year][0]
            state=analog_weights(entry['x'][past],query,lead,k=20)
            targets=np.array([entry['normal'][i]+predictions[i]['prediction'] for i in range(2)])
            distance=np.sum(((samples[:,:2]-targets)/scale[:2])**2,axis=1)
            conditional=np.exp(-.5*np.minimum(distance,40))*(.5+len(state)*state*.5);conditional/=conditional.sum()
            snow_cases.append(dict(id=station['id'],region=verify.region(station),year=year,actual=actual,
                samples=samples[:,2],conditional=conditional,climo=np.full(len(samples),1/len(samples))))
    snow_report=verify.evaluate_snow(snow_cases)
    points={v:[] for v in ['temperature','precipitation','snowfall']}
    for entry in prepared:
        station=entry['station'];normal=entry['normal'];scale=entry['scale'];y=entry['y'];weights=entry['state_weights']
        means=[]
        for column,variable in enumerate(['temperature','precipitation']):
            deployment=evaluated[variable]['deployed'][verify.region(station)]
            parameters=deployment['parameters'];cal=deployment['calibration'];alpha=parameters['alpha']
            stats=statistical_predictions(entry['x'],y,entry['years'],entry['query'],init[0],column,lead,normal[column])
            stat=stats[parameters['variant']]
            anomaly=alpha*entry['model'][variable]+(1-alpha)*stat
            centered=cal['residual']-np.mean(cal['residual'])
            draws=normal[column]+anomaly+centered*scale[column]
            if variable=='precipitation':draws=np.maximum(0,draws)
            # Small-sample probabilities retain climatological mass rather than
            # reporting deterministic certainty from a handful of hindcasts.
            ref=entry['samples'][:,column];ref=ref[np.isfinite(ref)]
            above=cal['strength']*np.mean(draws>normal[column])+(1-cal['strength'])*np.mean(ref>normal[column])
            below=cal['strength']*np.mean(draws<normal[column])+(1-cal['strength'])*np.mean(ref<normal[column])
            mean=float(draws.mean());means.append(mean)
            points[variable].append(dict(id=station['id'],name=station['name'],lat=station['lat'],lon=station['lon'],
                normal=float(normal[column]),anomaly=mean-float(normal[column]),above=float(above*100),below=float(below*100),
                expected=mean,range_low=float(np.quantile(draws,.1)),range_high=float(np.quantile(draws,.9)),
                median=float(np.median(draws)),region=verify.region(station),feature_variant=parameters['variant'],probability_model_strength=cal['strength'],normal_years=int(entry['counts'][column]),analog_count=int(len(y)),model_weight=alpha,recent_conditions_interpolated=entry['recent_imputed'],
                drivers=dict(raw_model_anomaly=entry['raw_models'][variable],bias_adjustment=entry['bias_terms'][variable],model_anomaly=entry['model'][variable],statistical_anomaly=stat,weighted_anomaly=anomaly,residual_mean_shift=0.)))
        snow_valid=np.isfinite(y).all(axis=1)
        if entry['counts'][2]<24 or snow_valid.sum()<24:continue
        ys=y[snow_valid];state=analog_weights(entry['x'][snow_valid],entry['query'],lead,k=20)
        distance=((ys[:,0]-means[0])/scale[0])**2+((ys[:,1]-means[1])/scale[1])**2
        conditional=np.exp(-.5*np.minimum(distance,40))*(.5+len(state)*state*.5)
        conditional/=conditional.sum()
        strength=snow_report['strengths'].get(verify.region(station),0.)
        conditional=strength*conditional+(1-strength)/len(conditional)
        snow=ys[:,2].copy();observed_snow=0.
        prefix=[m for m in months(start,duration_months) if m<init]
        if prefix:
            actual=np.array([station['series'].get(m,[np.nan]*3)[2] for m in prefix])
            if not np.isfinite(actual).all():continue
            observed_snow=float(actual.sum())
            candidate_years=entry['years'][snow_valid]
            prior=[]
            for yy in candidate_years:
                past_start=add_month(int(yy),init[1],lead)
                historical_prefix=months(past_start,len(prefix))
                prior.append(sum(station['series'].get(m,[np.nan]*3)[2] for m in historical_prefix))
            snow=np.maximum(0,snow-np.array(prior))+observed_snow
        expected=float(conditional@snow);mean=float(normal[2])
        band=min(len(SNOW_LABELS)-1,max(0,int(np.searchsorted(SNOW_BANDS,expected,side='right')-1)))
        points['snowfall'].append(dict(id=station['id'],name=station['name'],lat=station['lat'],lon=station['lon'],normal=mean,
            anomaly=expected-mean,above=float(100*conditional[snow>mean].sum()),below=float(100*conditional[snow<mean].sum()),
            expected=expected,amount=expected,total=expected,observed_snowfall_in=observed_snow,range_label=SNOW_LABELS[band]+' in',
            range_low=weighted_quantile(snow,conditional,.1),range_high=weighted_quantile(snow,conditional,.9),
            median=weighted_quantile(snow,conditional,.5),region=verify.region(station),conditional_strength=strength,
            exceedance={str(t):float(100*conditional[snow>=t].sum()) for t in (1,3,6,12,24)},
            normal_years=int(entry['counts'][2]),analog_count=len(snow),effective_sample_size=float(1/np.sum(conditional**2))))
    for variable,records in points.items():
        if (len(records)<(50 if duration_months==6 else 80) or min(r['lon'] for r in records)>-120 or max(r['lon'] for r in records)<-72
                or min(r['lat'] for r in records)>(34 if variable=='snowfall' else 27) or max(r['lat'] for r in records)<46):
            raise ValueError('Insufficient CONUS station count or geographic span for '+variable+': '+str(len(records)))
    return points,dict(weights=diagnostics,oni_reference_month=f'{latest[0]}-{latest[1]:02d}',
        atmospheric_reference_month=f'{latest_index[0]}-{latest_index[1]:02d}',
        sample_stations={v:len(p) for v,p in points.items()},model_components=list(MODELS),
        method='Equal model means form one dynamical stream; regional nested year-held-out fitting selects observed-state/trend predictors and stream weights. Snow uses historical snowfall with conditional strength chosen by earlier-year CRPS scoring.',
        verification={**{v:evaluated[v]['report'] for v in evaluated},'snowfall':snow_report},
        snow_warning='Experimental conditional historical snow distribution, limited-history, year-held-out evaluation; not a validated operational snowfall product. Broad amount bands classify the central estimate, not a confidence interval.')
