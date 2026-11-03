(()=>{'use strict';



const by=id=>document.getElementById('seasonal-'+id),model=by('model'),variable=by('variable'),metric=by('metric'),windowSelect=by('window'),city=by('city'),image=by('image');



let manifest,active,values,serial=0;const base=new URL('../generated/seasonal/',document.baseURI),cache=new Map();



const safe=name=>{if(!/^[a-z0-9-]+\.(png|json)$/.test(name))throw Error('Invalid seasonal asset');return new URL(name,base);};



function state(){history.replaceState(null,'','?'+new URLSearchParams({model:model.value,variable:variable.value,metric:metric.value,season:windowSelect.value}));}



function cityValue(){by('city-result').replaceChildren();if(!values||!city.value)return;const point=values.stations.find(p=>p.id===city.value);if(!point)return;const label=document.createElement('p');label.textContent=point.name;const number=document.createElement('div');number.className='seasonal-city-value';number.textContent=metric.value==='amount'?point.range_label:metric.value==='total'?Math.round(point.total)+' in (central estimate)':metric.value==='anomaly'?(point.anomaly>0?'+':'')+point.anomaly.toFixed(1)+(variable.value==='temperature'?' °F':' in'):point[metric.value].toFixed(0)+'%';const note=document.createElement('p');const blended=model.value==='blend';note.textContent=blended?(metric.value==='total'?'Central estimate for the entire selected snow season; the Expected range view shows broad bands for the same forecast.':metric.value==='amount'?'Broad band for the experimental central estimate; not a storm total or confidence interval.':metric.value==='anomaly'?'Experimental seasonal departure from the station normal.':'Experimental distribution fraction '+metric.value+' average; limited-history experimental probabilities; see the verification below.'):(metric.value==='anomaly'?'Average historical departure from this climate record normal.':'Historical fraction of comparable seasons '+metric.value+' the arithmetic average; not forecast odds.');const sample=document.createElement('p');sample.className='source-note';sample.textContent=point.analog_count+' historical seasons / '+point.normal_years+' normal seasons. Seasonal average: '+point.normal.toFixed(1)+(variable.value==='temperature'?' °F':' in')+'.';by('city-result').append(label,number,note,sample);if(blended&&point.drivers){const driver=document.createElement('p');driver.className='source-note';const d=point.drivers;driver.textContent='Drivers: six-model mean '+d.raw_model_anomaly.toFixed(2)+(variable.value==='temperature'?' °F':' in')+'; state/analog stream '+d.statistical_anomaly.toFixed(2)+'; model weight '+Math.round(point.model_weight*100)+'%. No added anomaly offset; the error distribution is centered.';by('city-result').append(driver);}if(blended){const range=document.createElement('p');const unit=variable.value==='temperature'?' °F':' in';range.textContent='Historical scenario range (10th–90th percentile): '+Math.floor(point.range_low)+'–'+Math.ceil(point.range_high)+unit+'. Check the held-out interval coverage below; it may differ substantially from 80%.';by('city-result').append(range);if(Number.isFinite(point.median)){const p=document.createElement('p');p.textContent='Distribution median: '+point.median.toFixed(1)+unit+'. A skewed distribution can have a higher mean than median.';by('city-result').append(p);}if(point.exceedance){const p=document.createElement('p');p.textContent='Experimental chance of at least: '+Object.entries(point.exceedance).map(([t,v])=>t+' in: '+Math.round(v)+'%').join(' / ')+'.';by('city-result').append(p);}}}

function blendInfo(){const panel=by('blend-inputs');panel.replaceChildren();const info=manifest.blend?.find(x=>(x.period_id||x.season_start)===windowSelect.value);if(!info)return;const models=document.createElement('p');models.textContent='Model components: '+info.model_components.join(' / ')+'.';panel.append(models);if(manifest.external_guidance?.status==='not_connected'){const p=document.createElement('p');p.className='source-note';p.textContent='Additional independent centers: not connected. They need matching hindcasts and verification before inclusion.';panel.append(p);}const coverage=document.createElement('p');coverage.textContent='Contributing blend records: '+Object.entries(info.sample_stations).map(([k,n])=>k+' '+n).join(' / ')+'. Snowfall-normal source network: '+(manifest.observations.snow_normals?.station_count||'pending')+' stations.';panel.append(coverage);for(const [name,w]of Object.entries(info.weights)){const p=document.createElement('p');p.textContent=name[0].toUpperCase()+name.slice(1)+': '+Math.round(w.model_weight*100)+'% model stream / '+Math.round(w.statistical_weight*100)+'% observed-state statistical stream. Development cases: '+w.development_cases+'.';panel.append(p);}const snapshot=document.createElement('p');snapshot.textContent='Atmospheric reference month: '+info.atmospheric_reference_month+' · ENSO reference: '+info.oni_reference_month+'.';panel.append(snapshot);verificationInfo(info);for(const [name,value]of Object.entries(manifest.atmosphere||{})){const span=document.createElement('span');span.className='seasonal-index-chip';span.textContent=name.toUpperCase()+' '+(value.value>0?'+':'')+(Number.isFinite(value.value)?value.value.toFixed(2):'unavailable')+' / '+value.latest_month;panel.append(span);}}



function verificationInfo(info){

 const panel=by('verification');panel.replaceChildren();

 const heading=document.createElement('h2');heading.textContent='Tested against earlier winters.';panel.append(heading);

 const intro=document.createElement('p');intro.textContent='Each test year is forecast using settings selected on earlier years. Stations within one winter are correlated. These checks describe this archive, not guaranteed future skill.';panel.append(intro);

 const table=document.createElement('table');table.className='seasonal-verification-table';

 const header=document.createElement('tr');for(const title of ['Variable','Test winters','Error / reference','Skill vs reference']){const th=document.createElement('th');th.textContent=title;header.append(th);}table.append(header);

 for(const [name,report] of Object.entries(info.verification||{})){

  const r=report.overall,row=document.createElement('tr'),snow=name==='snowfall',skill=snow?r.crps_skill:r.mse_skill_vs_climatology;

  const error=snow?r.crps:r.rmse,reference=snow?r.climatology_crps:r.climatology_rmse;

  for(const text of [name,(r.years||[]).join(', ')||'Insufficient history',Number.isFinite(error)?error.toFixed(2)+' / '+reference.toFixed(2)+(name==='temperature'?' °F':' in'):'Not scored',Number.isFinite(skill)?(100*skill).toFixed(1)+'%':'Not scored']){const td=document.createElement('td');td.textContent=text;row.append(td);}table.append(row);

  const detail=document.createElement('details'),summary=document.createElement('summary');summary.textContent=name+' · regional checks';detail.append(summary);

  for(const [region,r]of Object.entries(report.regions||{})){const p=document.createElement('p');const skill=snow?r.crps_skill:r.mse_skill_vs_climatology;p.textContent=region+': '+(r.years||[]).length+' test winters; '+(Number.isFinite(skill)?(100*skill).toFixed(1)+'% skill vs climatology':'insufficient history')+(Number.isFinite(r.interval_80_coverage)?'; scenario interval coverage '+Math.round(100*r.interval_80_coverage)+'%':'')+'.';detail.append(p);}panel.append(detail);

 }

 panel.insertBefore(table,panel.children[2]||null);

 const note=document.createElement('p');note.className='source-note';note.textContent='Temperature and precipitation skill uses mean squared error; snow uses CRPS for the entire distribution. Negative skill means climatology performed better. Fixed 1991–2020 normals and changing historical model versions limit this retrospective comparison.';panel.append(note);

}



async function draw(){if(!manifest)return;const chosenWindow=manifest.windows.find(w=>(w.id||w.start)===windowSelect.value);if(chosenWindow?.duration_months===6){model.value='blend';variable.value='snowfall';}const request=++serial;values=null;city.disabled=true;city.replaceChildren(new Option('Available with Blend or analogs',''));by('city-result').replaceChildren();



 if(variable.value==='snowfall'&&!['blend','analogs'].includes(model.value))model.value='blend';



 for(const option of metric.options)option.disabled=(!['nmme','analogs','blend'].includes(model.value)&&option.value!=='anomaly')||(['analogs','blend'].includes(model.value)&&option.value==='near')||(option.value==='amount'&&(model.value!=='blend'||variable.value!=='snowfall'))||(option.value==='total'&&chosenWindow?.duration_months!==6);



 if(metric.selectedOptions[0].disabled)metric.value='anomaly';



 const item=manifest.products.find(p=>p.model===model.value&&p.variable===variable.value&&p.metric===metric.value&&(p.period_id||p.season_start)===windowSelect.value);state();



 if(!item){image.hidden=true;by('empty').hidden=false;by('empty').textContent='This combination is unavailable in the current data.';return;}



 active=item;blendInfo();by('map-title').textContent=item.title;by('valid').textContent=item.season_label+' / initialized '+item.initialization_month;const imageUrl=safe(item.image_filename);imageUrl.searchParams.set('v',item.image_sha256);image.src=imageUrl;image.alt=item.title+' for '+item.season_label+', '+item.model_label;image.hidden=false;by('empty').hidden=true;by('download').href=safe(item.image_filename);



 const historical=model.value==='analogs',blended=model.value==='blend';for(const option of metric.options){if(['above','below'].includes(option.value))option.textContent=(historical||blended)?option.value[0].toUpperCase()+option.value.slice(1)+(historical?' average · historical':' average · experimental'):option.value[0].toUpperCase()+option.value.slice(1)+' normal';}by('context').textContent=blended?(metric.value==='total'?'Full-period snowfall central estimate in inches · not a sum of overlapping three-month forecasts.':metric.value==='amount'?'Expected seasonal snowfall band · central estimate, not a confidence interval · broader scenario range in the city view.':'CH Weather research blend · experimental outcomes relative to the arithmetic average · observational support varies; see the coverage note below.'):historical?'Historical ENSO composite · smooth station-based contours · coverage varies; frequencies describe past seasons, not forecast odds.':metric.value==='anomaly'?'Model-relative anomaly · three-month mean temperature or accumulated precipitation departure · native 1° guidance.':'NOAA CPC adjusted NMME probabilities · upper, middle, or lower climatological third · all three categories sum to 100%.';



 if(item.limited_observation_support_land_percent!==undefined)by('context').textContent+=' Limited nearby observation support / edge extension: '+item.limited_observation_support_land_percent+'% of CONUS land.';

 by('explainer-heading').textContent=blended?'One outlook. Several sources.':historical?'History provides context.':'A season is not a daily forecast.';



 by('explainer').textContent=blended?'The CH Weather Blend combines six current climate-model components with an observed-state statistical stream. Snow guidance uses measured historical snowfall conditioned on the blended climate pattern. Select a station to inspect the estimate, normal and uncertainty.':historical?'Contours combine long-record cooperative stations and city climate records. Edge extrapolation and weaker support are summarized below. Each location can have fewer than ten usable analogs, so check the sample size.':'NMME is the main guidance. CFSv2 and CanSIPS are component comparisons, not additional independent votes. These maps describe a three-month pattern, not individual storms.';



 try{const valueUrl=safe(item.values_filename);valueUrl.searchParams.set('v',item.image_sha256);const url=valueUrl.href;if(!cache.has(url))cache.set(url,fetch(url).then(r=>{if(!r.ok)throw Error('Map values unavailable');return r.json();}));const data=await cache.get(url);if(request!==serial)return;values=data;if(historical||blended){city.replaceChildren(new Option('Choose a city',''));for(const p of [...data.stations].sort((a,b)=>a.name.localeCompare(b.name)))city.add(new Option(p.name,p.id));city.disabled=false;}}catch(error){if(request===serial){by('city-result').textContent=error.message;}}



}



(async()=>{try{const response=await fetch(new URL('latest.json',base),{cache:'no-cache'});if(!response.ok)throw Error('Seasonal guidance has not been published yet.');manifest=await response.json();if(manifest.status==='unavailable'||!manifest.products?.length)throw Error(manifest.message||'Seasonal refresh pending.');const query=new URLSearchParams(location.search);for(const [key,select]of [['model',model],['variable',variable],['metric',metric]])if([...select.options].some(o=>o.value===query.get(key)))select.value=query.get(key);for(const w of manifest.windows)windowSelect.add(new Option(w.label,w.id||w.start));windowSelect.disabled=false;if([...windowSelect.options].some(o=>o.value===query.get('season')))windowSelect.value=query.get('season');



 const analog=manifest.analog_selection,latest=analog.latest_observed;by('phase').textContent=analog.phase+' analogs';by('oni').textContent='Observed '+latest.season+' '+latest.year+' ONI: '+(latest.anomaly_c>0?'+':'')+latest.anomaly_c.toFixed(2)+' °C. '+analog.selected.length+' closest independent historical matches.';for(const r of analog.selected){const span=document.createElement('span');span.textContent=r.year+' / '+(r.anomaly_c>0?'+':'')+r.anomaly_c.toFixed(2);by('years').append(span);}



 by('status').textContent='Model initialization: '+manifest.model_run+' · generated '+new Date(manifest.generated_at_utc).toLocaleString(undefined,{timeZone:'UTC',timeZoneName:'short'})+' · '+manifest.windows.filter(w=>w.duration_months!==6).length+' rolling windows'+(manifest.windows.some(w=>w.duration_months===6)?' + full November–April snow season':'');by('source-date').textContent='Observed climate records through '+manifest.observations.observation_end_month+'. Normal comparison: '+manifest.normal_period+'. NOAA model-relative anomalies retain their publisher climatology.';



 const full=manifest.windows.find(w=>w.duration_months===6);if(full){by('fullseason').hidden=false;by('fullseason').onclick=event=>{event.preventDefault();windowSelect.value=full.id;model.value='blend';variable.value='snowfall';metric.value='total';draw();document.querySelector('.seasonal-console').scrollIntoView();};}

 for(const select of [model,variable,metric,windowSelect])select.addEventListener('change',()=>{const selected=manifest.windows.find(w=>(w.id||w.start)===windowSelect.value);if(selected?.duration_months===6&&((select===model&&model.value!=='blend')||(select===variable&&variable.value!=='snowfall'))){const regular=manifest.windows.find(w=>w.duration_months!==6);windowSelect.value=regular.id||regular.start;}if(select===model&&!['blend','analogs'].includes(model.value)&&variable.value==='snowfall')variable.value='temperature';draw();});city.addEventListener('change',cityValue);await draw();



}catch(error){by('status').textContent=error.message;by('status').classList.add('seasonal-error');}})();



image.addEventListener('error',()=>{by('empty').hidden=false;by('empty').textContent='The map could not be loaded. Try refreshing or choose another season.';image.hidden=true;});



})();



