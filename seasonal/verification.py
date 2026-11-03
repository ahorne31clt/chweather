"""Year-blocked, nested seasonal verification and conservative calibration.

All tuning for a held-out initialization year uses strictly earlier years.
Published climate normals define the reference; anomaly archives still contain
historical model-version changes, so these results are not homogeneous reforecasts.
"""
from collections import defaultdict
import numpy as np
from scipy.special import ndtr

VARIANTS=('base','trend','extended','extended_trend')


def region(station):
    lon,lat=station['lon'],station['lat']
    if station.get('state')=='NC' or station.get('id') in ('CLT','AVL','RDU','GSO','ILM'):
        return 'NC mountains' if lon< -81 else 'NC coast' if lon> -78.5 else 'NC Piedmont'
    if lon< -106:return 'West'
    if lon< -94:return 'Plains'
    if lat>=39:return 'Northeast / Great Lakes'
    return 'Southeast'


def year_loss(cases,predictions):
    years=np.array([r['year'] for r in cases]);truth=np.array([r['actual'] for r in cases]);scale=np.array([r['scale'] for r in cases])
    error=((predictions-truth)/scale)**2
    return float(np.mean([np.mean(error[years==year]) for year in np.unique(years)]))


def fit(cases,prior=None):
    if len({r['year'] for r in cases})<4:return None
    candidates=[]
    for variant in VARIANTS:
        subset=[r for r in cases if np.isfinite(r['stats'].get(variant,np.nan))]
        if len(subset)<30 or len({r['year'] for r in subset})<4:continue
        for alpha in np.linspace(0,1,11):
            prediction=np.array([alpha*r['model']+(1-alpha)*r['stats'][variant] for r in subset])
            penalty=.02*(alpha-(prior['alpha'] if prior else .7))**2+.005*(variant!='base')
            candidates.append((year_loss(subset,prediction)+penalty,float(alpha),variant))
    if not candidates:return None
    _,alpha,variant=min(candidates,key=lambda r:r[0])
    if prior:
        shrink=len({r['year'] for r in cases})/(len({r['year'] for r in cases})+8)
        alpha=shrink*alpha+(1-shrink)*prior['alpha']
    return dict(alpha=float(alpha),variant=variant,training_years=sorted({r['year'] for r in cases}))


def predict(case,parameters):
    stat=case['stats'].get(parameters['variant'],np.nan)
    if not np.isfinite(stat):stat=case['stats']['base']
    return parameters['alpha']*case['model']+(1-parameters['alpha'])*stat


def weighted_crps(samples,weights,actual):
    samples=np.asarray(samples,dtype=float);weights=np.asarray(weights,dtype=float);weights=weights/weights.sum()
    order=np.argsort(samples);x=samples[order];w=weights[order]
    pair=np.sum(w*x*(2*np.cumsum(w)-w-1))
    return float(np.sum(w*np.abs(x-actual))-pair)


def score(rows):
    if not rows:return dict(status='insufficient_history',years=[],cases=0)
    years=sorted({r['year'] for r in rows})
    def average(key):return float(np.mean([np.mean([r[key] for r in rows if r['year']==year]) for year in years]))
    mse=average('squared_error');baseline=average('climo_squared_error');raw=average('model_squared_error')
    brier=average('brier');climo_brier=average('climo_brier')
    reliability=[]
    for low in np.arange(0,1,.2):
        selected=[r for r in rows if low<=r['probability']<(low+.2 if low<.8 else 1.001)]
        if selected:reliability.append(dict(lower=float(low),upper=float(low+.2),cases=len(selected),forecast=float(np.mean([r['probability'] for r in selected])),observed=float(np.mean([r['event'] for r in selected]))))
    # Bootstrap initialization years, never station cases as independent winters.
    rng=np.random.default_rng(20261101);blocks=np.array([np.mean([r['squared_error'] for r in rows if r['year']==year]) for year in years])
    draws=np.sqrt(np.mean(blocks[rng.integers(0,len(years),(500,len(years)))],axis=1))
    return dict(status='rolling_year_holdout',years=years,cases=len(rows),independent_initialization_years=len(years),rmse=float(np.sqrt(mse)),
        climatology_rmse=float(np.sqrt(baseline)),raw_model_rmse=float(np.sqrt(raw)),mse_skill_vs_climatology=1-mse/baseline if baseline else None,
        mse_skill_vs_raw_model=1-mse/raw if raw else None,brier=brier,climatology_brier=climo_brier,
        brier_skill=1-brier/climo_brier if climo_brier else None,interval_80_coverage=average('covered'),
        rmse_year_bootstrap_90=[float(v) for v in np.quantile(draws,[.05,.95])],reliability=reliability,
        warning='Historical operational archives change model versions; limited independent winters. Smoothing does not enter scoring.')


def calibration(cases,parameters):
    residual=np.array([(r['actual']-predict(r,parameters))/r['scale'] for r in cases])
    residual-=np.mean(residual)
    spread=max(float(np.std(residual)),.5)
    raw=np.array([np.mean(predict(r,parameters)+residual*r['scale']>0) for r in cases])
    truth=np.array([r['actual']>0 for r in cases],dtype=float);climo=np.array([r['climo_probability'] for r in cases])
    strengths=np.linspace(0,1,11)
    loss=[]
    for strength in strengths:
        probability=strength*raw+(1-strength)*climo
        loss.append(float(np.mean((probability-truth)**2))+.005*strength**2)
    return dict(strength=float(strengths[int(np.argmin(loss))]),spread=spread,residual=residual)


def evaluate(cases):
    """Fit each outer year on earlier years; regional estimates shrink to CONUS."""
    years=sorted({r['year'] for r in cases});rows=[];by_case={}
    for year in years:
        training=[r for r in cases if r['year']<year]
        global_fit=fit(training)
        if global_fit is None:continue
        for name in sorted({r['region'] for r in cases}):
            local=[r for r in training if r['region']==name]
            parameters=fit(local,global_fit) or global_fit
            training_for_calibration=local if len(local)>=30 else training
            cal=calibration(training_for_calibration,parameters)
            for case in [r for r in cases if r['year']==year and r['region']==name]:
                value=predict(case,parameters);error=case['actual']-value
                raw=float(np.mean(value+cal['residual']*case['scale']>0))
                probability=cal['strength']*raw+(1-cal['strength'])*case['climo_probability']
                low,high=value+np.quantile(cal['residual'],[.1,.9])*case['scale']
                row=dict(id=case['id'],year=year,region=name,prediction=float(value),actual=case['actual'],scale=case['scale'],parameters=parameters,
                    squared_error=error**2,climo_squared_error=case['actual']**2,model_squared_error=(case['actual']-case['model'])**2,
                    probability=float(probability),event=float(case['actual']>0),brier=float((probability-(case['actual']>0))**2),
                    climo_brier=float((case['climo_probability']-(case['actual']>0))**2),covered=float(low<=case['actual']<=high))
                rows.append(row);by_case[case['id'],year]=row
    global_fit=fit(cases)
    if global_fit is None:raise ValueError('Insufficient archive for regional calibration')
    deployed={};summary={}
    for name in sorted({r['region'] for r in cases}):
        local=[r for r in cases if r['region']==name];parameters=fit(local,global_fit) or global_fit
        deployed[name]=dict(parameters=parameters,calibration=calibration(local if len(local)>=30 else cases,parameters))
        summary[name]=score([r for r in rows if r['region']==name])
    return dict(deployed=deployed,rows=rows,by_case=by_case,report=dict(overall=score(rows),regions=summary,
        method='Strict forward initialization-year outer holdout. Each held-out year uses earlier years for stream/feature selection and probability shrinkage. Each winter has equal weight in fitting.'))


def snow_mixture_strength(cases):
    if len({r['year'] for r in cases})<3:return 0.
    choices=[]
    for strength in np.linspace(0,1,6):
        losses=[]
        for year in sorted({r['year'] for r in cases}):
            losses.append(np.mean([weighted_crps(r['samples'],strength*r['conditional']+(1-strength)*r['climo'],r['actual']) for r in cases if r['year']==year]))
        choices.append(float(np.mean(losses))+.01*strength**2)
    return float(np.linspace(0,1,6)[int(np.argmin(choices))])


def evaluate_snow(cases):
    rows=[]
    for year in sorted({r['year'] for r in cases}):
        training=[r for r in cases if r['year']<year]
        if len({r['year'] for r in training})<3:continue
        for case in [r for r in cases if r['year']==year]:
            local=[r for r in training if r['region']==case['region']]
            strength=snow_mixture_strength(local if len(local)>=20 else training)
            weights=strength*case['conditional']+(1-strength)*case['climo']
            rows.append(dict(year=year,region=case['region'],crps=weighted_crps(case['samples'],weights,case['actual']),
                climatology_crps=weighted_crps(case['samples'],case['climo'],case['actual'])))
    def summary(selected):
        years=sorted({r['year'] for r in selected})
        if not years:return dict(status='insufficient_history',years=[],cases=0)
        mean=lambda key:float(np.mean([np.mean([r[key] for r in selected if r['year']==y]) for y in years]))
        baseline=mean('climatology_crps');error=mean('crps')
        return dict(status='rolling_year_holdout',years=years,cases=len(selected),crps=error,climatology_crps=baseline,
            crps_skill=1-error/baseline if baseline else None)
    regions=sorted({r['region'] for r in cases})
    return dict(overall=summary(rows),regions={r:summary([v for v in rows if v['region']==r]) for r in regions},
        strengths={r:snow_mixture_strength([v for v in cases if v['region']==r]) for r in regions},
        method='Forward year holdout. Snow uses temperature/precipitation predictions made without the verifying year. Earlier winters select conditional-versus-climatological strength by CRPS. Limited and changing operational archive.')
