(()=>{'use strict';
 const $=id=>document.getElementById('optics-'+id),base=new URL('../generated/optics/',document.baseURI);
 let manifest,locations,kind='halo',region='national';
 const safe=name=>{if(!/^[a-z0-9-]+\.(png|json)$/.test(name))throw Error('Invalid optics filename');return new URL(name,base);};
 const format=t=>new Date(t).toLocaleString(undefined,{timeZone:$('zone').value==='UTC'?'UTC':undefined,month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
 function city(){
  $('hours').replaceChildren();const place=locations?.locations[Number($('city').value)];if(!place)return;
  const scores=place.scores[kind],maximum=Math.max(...scores),best=scores.indexOf(maximum);
  const eligible=place.solar_elevation_degrees.some(a=>kind==='horizontal'?a>58:kind==='zenithal'?a>0&&a<32:kind==='rainbow'?a>0&&a<42:a>0);
  $('best').textContent=!eligible?'Solar geometry does not permit this display in the selected window.':maximum<10?'No notable ingredient signal at this model grid point.':'Best sampled ingredient signal: '+maximum+'/100 near '+format(locations.times[best])+'. This is not a probability.';
  for(let i=0;i<scores.length;i++){
   const row=document.createElement('tr');const time=document.createElement('th');time.scope='row';time.textContent=format(locations.times[i]);const altitude=document.createElement('td');altitude.textContent=place.solar_elevation_degrees[i].toFixed(1)+'°';const score=document.createElement('td');const bar=document.createElement('span');bar.className='optics-bar';bar.style.setProperty('--score',scores[i]+'%');bar.textContent=scores[i]+' / 100';score.append(bar);row.append(time,altitude,score);$('hours').append(row);
  }
  const f=place.hourly_ingredients?.[best];$('ingredients').replaceChildren();
  if(place.gfs_scores?.[kind]){const p=document.createElement('p');p.textContent='At this hour: displayed guidance '+scores[best]+'/100; GFS-only comparison '+place.gfs_scores[kind][best]+'/100. A difference reflects cloud-model disagreement, not measured forecast confidence.';$('ingredients').append(p);}
  if(f){const p=document.createElement('p');p.textContent='Inputs at the best sampled hour: high cloud '+f.high.toFixed(0)+'%, middle '+f.middle.toFixed(0)+'%, low '+f.low.toFixed(0)+'%; visibility '+(f.visibility/1000).toFixed(1)+' km; grid-point total precipitation rate '+(f.rate*3600).toFixed(2)+' mm/h; rain flag/fraction '+f.rain.toFixed(2)+'. Rainbow scoring uses nearby antisolar rain, which can differ from this point.';$('ingredients').append(p);for(const level of [300,400,500]){const p=document.createElement('p');p.textContent=level+' hPa: '+(f['temp'+level]-273.15).toFixed(1)+' °C / RH '+f['rh'+level].toFixed(0)+'% / cloud ice '+(f['ice'+level]*1000).toFixed(4)+' g/kg.';$('ingredients').append(p);}}
 }
 function draw(){
  if(!manifest)return;const product=manifest.products.find(p=>p.id===kind&&p.region===region);if(!product)throw Error('This optics map is unavailable');
  const url=safe(product.image_filename);url.searchParams.set('v',product.image_sha256);$('image').src=url;$('image').alt=product.title+' best hourly ingredient favorability for '+region;$('download').href=url;$('title').textContent=product.title;$('description').textContent=product.description;
  $('dates').textContent='Valid '+format(manifest.valid_start_utc)+' to '+format(manifest.valid_end_utc)+' · GFS run '+format(manifest.model_run)+' · generated '+format(manifest.generated_at_utc);
  $('models').textContent=manifest.hrrr?.status==='available'?'Hourly HRRR cloud refinement · HRRR run '+format(manifest.hrrr.model_run)+' · GFS upper-air/rain · sampled on a 0.25° grid. Satellite observations are shown separately.':'GFS guidance · HRRR refinement unavailable for this window. No HRRR input has been invented.';
  for(const b of document.querySelectorAll('[data-phenomenon]'))b.setAttribute('aria-pressed',String(b.dataset.phenomenon===kind));
  for(const b of document.querySelectorAll('[data-optics-region]'))b.setAttribute('aria-pressed',String(b.dataset.opticsRegion===region));
  history.replaceState(null,'','?'+new URLSearchParams({phenomenon:kind,region}));city();
 }
 (async()=>{try{
  const response=await fetch(new URL('latest.json',base),{cache:'no-cache'});if(!response.ok)throw Error('Solar-optics guidance has not been published yet.');manifest=await response.json();if(!manifest.products?.length)throw Error('No validated optics run is available.');
  const query=new URLSearchParams(location.search);if([...$('phenomenon').options].some(o=>o.value===query.get('phenomenon')))kind=query.get('phenomenon');region=query.get('region')==='nc'?'nc':'national';$('phenomenon').value=kind;$('region').value=region;
  const stale=Date.now()>Date.parse(manifest.valid_end_utc)||Date.now()-Date.parse(manifest.generated_at_utc)>24*3600000;
  $('status').textContent=stale?'Earlier guidance · its valid window may have ended. Check the timestamps.':'Real model inputs · experimental ingredient guidance, not event probabilities.';
  draw();const values=await fetch(safe(manifest.locations_filename),{cache:'no-cache'});if(!values.ok)throw Error('City viewing times are unavailable');locations=await values.json();$('city').replaceChildren();locations.locations.forEach((p,i)=>$('city').add(new Option(p.name,String(i))));const clt=locations.locations.findIndex(p=>p.name.toLowerCase().includes('charlotte'));$('city').value=String(Math.max(0,clt));$('city').disabled=false;city();
  const observations=manifest.satellite?.observations||[];$('satellite-select').replaceChildren();
  observations.forEach((p,i)=>$('satellite-select').add(new Option(p.platform+' / '+(p.band==='04'?'Cirrus · daytime':'Infrared · day/night'),String(i))));
  function showSatellite(){const p=observations[Number($('satellite-select').value)];if(!p){$('satellite-status').textContent='No fresh satellite observation was available during generation. Forecast guidance remains separate.';return;}$('satellite-image').src=safe(p.image_filename);$('satellite-image').hidden=false;$('satellite-note').textContent=p.description;$('satellite-status').textContent='Observed '+format(p.observed_at_utc)+(Date.now()-Date.parse(p.observed_at_utc)>2*3600000?' · Earlier snapshot; open the satellite viewer for newer imagery.':' · NOAA GOES observation.');}
  $('satellite-select').onchange=showSatellite;showSatellite();
 }catch(error){$('status').textContent=error.message;}})();
 $('phenomenon').onchange=()=>{kind=$('phenomenon').value;draw();};$('region').onchange=()=>{region=$('region').value;draw();};$('city').onchange=city;$('zone').onchange=draw;
 for(const b of document.querySelectorAll('[data-phenomenon]'))b.onclick=()=>{kind=b.dataset.phenomenon;$('phenomenon').value=kind;draw();};
 for(const b of document.querySelectorAll('[data-optics-region]'))b.onclick=()=>{region=b.dataset.opticsRegion;$('region').value=region;draw();};
 $('image').onerror=()=>{$('status').textContent='The optics graphic could not be loaded. Check the latest generation workflow.';};
 $('worksheet').onclick=()=>{const place=locations?.locations[Number($('city').value)];if(!place)return;const lines=['utc_time,location,phenomenon,ingredient_score,sun_elevation_deg,model_run,observed_yes_no_unknown,cloud_notes,photo_reference'];locations.times.forEach((t,i)=>lines.push([t,place.name.replaceAll(',',' '),kind,place.scores[kind][i],place.solar_elevation_degrees[i],manifest.model_run,'','',''].join(',')));const url=URL.createObjectURL(new Blob([lines.join('\r\n')],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='ch-weather-optics-observations.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
})();
