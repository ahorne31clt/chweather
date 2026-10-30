// Official NWS point forecasts. No generated, illustrative, or substitute values.
const localForecastSection = document.querySelector('.local-forecast');
if (localForecastSection) {
  const section=localForecastSection;
  const form=section.querySelector('.nws-search');
  const input=form.querySelector('input');
  const status=section.querySelector('.nws-status');
  const content=section.querySelector('.nws-content');
  const matches=section.querySelector('.nws-matches');
  const loading=section.querySelector('.nws-loading');
  const memoryCache=new Map();
  let sequence=0, controller, current;
  const svgNS='http://www.w3.org/2000/svg';

  function element(parent,tag,text,className) {
    const node=document.createElement(tag);
    if(text!=null)node.textContent=text;
    if(className)node.className=className;
    parent.append(node);return node;
  }
  function temperature(period) {
    let value=period.temperature, unit=period.temperatureUnit;
    if(value && typeof value==='object') {unit=value.unitCode;value=value.value;}
    if(typeof value!=='number'||!Number.isFinite(value))return null;
    if(unit==='C'||unit==='wmoUnit:degC')value=value*9/5+32;
    else if(unit!=='F'&&unit!=='wmoUnit:degF')return null;
    return Math.round(value);
  }
  function probability(period) {
    const value=period.probabilityOfPrecipitation?.value;
    return typeof value==='number'&&value>=0&&value<=100?Math.round(value):null;
  }
  function wind(period) {
    let speed=period.windSpeed;
    if(speed && typeof speed==='object') {
      let value=speed.value;
      const factor={'wmoUnit:km_h':.621371,'wmoUnit:m_s':2.236936,'wmoUnit:mi_h':1}[speed.unitCode];
      speed=typeof value==='number'&&Number.isFinite(value)&&factor?Math.round(value*factor)+' mph':null;
    }
    return typeof speed==='string'&&speed.trim()?[period.windDirection,speed].filter(Boolean).join(' '):'Not provided';
  }
  function friendlyTime(date,timeZone,options={}) {
    const value=new Date(date);
    if(!Number.isFinite(value.getTime()))return 'Time not provided';
    return new Intl.DateTimeFormat('en-US',{timeZone,...options}).format(value);
  }
  function nwsURL(value) {
    const url=new URL(value);
    if(url.protocol!=='https:'||url.hostname!=='api.weather.gov')throw new Error('The NWS forecast endpoint is unavailable for this location.');
    return url;
  }
  async function getJSON(value,signal) {
    const url=nwsURL(value);
    for(let attempt=0;attempt<2;attempt++) {
      const response=await fetch(url,{headers:{Accept:'application/geo+json'},signal:AbortSignal.any([signal,AbortSignal.timeout(18000)])});
      if(!response.ok) {
        if(attempt===0&&[429,500,502,503,504].includes(response.status)) {await new Promise(resolve=>setTimeout(resolve,900));continue;}
        if(response.status===404)throw new Error('An NWS land forecast is not available at that point. Try a nearby city or open weather.gov.');
        throw new Error('The NWS forecast service is temporarily unavailable. Please try again or open weather.gov.');
      }
      return response.json();
    }
  }
  function weatherIcon(period,large=false) {
    const text=(period.shortForecast||'').toLowerCase();
    const source=(period.icon||'').toLowerCase();
    const svg=document.createElementNS(svgNS,'svg');svg.setAttribute('viewBox','0 0 100 100');
    svg.setAttribute('aria-hidden','true');svg.classList.add('weather-symbol');if(large)svg.classList.add('weather-symbol-large');
    const draw=(tag,attributes)=>{const node=document.createElementNS(svgNS,tag);Object.entries(attributes).forEach(([k,v])=>node.setAttribute(k,String(v)));svg.append(node);return node;};
    const stroke={fill:'none',stroke:'currentColor','stroke-width':3.2,'stroke-linecap':'square','stroke-linejoin':'miter'};
    const cloud=()=>draw('path',{...stroke,d:'M23 65H77C94 65 92 42 76 41C75 23 47 19 40 39C24 32 10 52 23 65Z'});
    const sun=(small=false)=>{draw('circle',{...stroke,cx:small?36:50,cy:small?34:50,r:small?14:19});const cx=small?36:50,cy=small?34:50;for(let i=0;i<8;i++){const a=i*Math.PI/4;draw('line',{...stroke,x1:cx+Math.cos(a)*(small?21:28),y1:cy+Math.sin(a)*(small?21:28),x2:cx+Math.cos(a)*(small?27:37),y2:cy+Math.sin(a)*(small?27:37)});}};
    const moon=()=>{draw('path',{...stroke,d:'M67 17C43 13 24 30 25 52C26 76 50 91 72 80C44 78 33 46 49 28C54 22 60 19 67 17Z'});draw('path',{...stroke,d:'M77 25V37M71 31H83'});};
    if(/thunder|tstorm|tsra|ts_/.test(text+' '+source)) {cloud();draw('path',{...stroke,stroke:'#C19244',d:'M53 65L42 82H55L48 96'});}
    else if(/snow|sleet|freezing|ice|\/sn|\/fz/.test(text+' '+source)) {cloud();[31,51,71].forEach(x=>draw('path',{...stroke,d:`M${x} 75V89M${x-6} 78L${x+6} 86M${x-6} 86L${x+6} 78`}));}
    else if(/rain|shower|drizzle|\/ra|shra/.test(text+' '+source)) {cloud();[31,51,71].forEach(x=>draw('path',{...stroke,d:`M${x} 75L${x-5} 88`}));}
    else if(/fog|haze|smoke/.test(text)) {cloud();[75,86].forEach(y=>draw('path',{...stroke,d:`M20 ${y}H80`}));}
    else if(/cloud|overcast|bkn|ovc|sct|few/.test(text+' '+source)) {if(period.isDaytime)sun(true);cloud();}
    else if(period.isDaytime===false)moon();
    else if(/sunny|clear|skc/.test(text+' '+source))sun();
    else if(/wind|breez/.test(text)) {draw('path',{...stroke,d:'M20 37H69C87 37 86 19 74 20M15 51H86M23 65H65C83 65 84 83 70 83'});}
    else {draw('path',{...stroke,d:'M42 58V23C42 10 58 10 58 23V58C79 74 65 94 50 94C32 94 22 74 42 58Z'});draw('path',{...stroke,d:'M50 36V76'});}
    return svg;
  }
  function link(parent,text,url,className='text-link') {
    const a=element(parent,'a',text,className);a.href=url;return a;
  }
  function stat(parent,label,value) {const item=element(parent,'div',null,'nws-stat');element(item,'dt',label);element(item,'dd',value);}

  function renderSelected(period) {
    const hero=content.querySelector('.nws-feature');hero.replaceChildren();
    hero.classList.toggle('nws-night',period.isDaytime===false);
    const primary=element(hero,'div',null,'nws-primary');
    element(primary,'p',period.name.toUpperCase()+' / '+(period.isDaytime===true?'FORECAST HIGH':period.isDaytime===false?'FORECAST LOW':'FORECAST TEMPERATURE'),'eyebrow');
    const figure=element(primary,'div',null,'nws-temperature-row');
    const temp=element(figure,'div',null,'nws-temperature');
    element(temp,'span',temperature(period)==null?'—':String(temperature(period)));element(temp,'small','°F');
    figure.append(weatherIcon(period,true));
    element(primary,'h4',period.shortForecast||'Forecast description not supplied','nws-condition');
    element(primary,'p',friendlyTime(period.startTime,current.timeZone,{weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+' – '+friendlyTime(period.endTime,current.timeZone,{weekday:'short',hour:'numeric',minute:'2-digit',timeZoneName:'short'}),'nws-valid');
    const detail=element(hero,'div',null,'nws-details');
    element(detail,'p','THE NWS FORECAST','eyebrow');
    element(detail,'p',period.detailedForecast||'A detailed forecast was not supplied for this period.','nws-narrative');
    const stats=element(detail,'dl',null,'nws-stats');
    const pop=probability(period);
    stat(stats,'Precipitation chance',pop==null?'Not provided':pop+'%');
    stat(stats,'Wind',wind(period));
    const note=element(detail,'p','Precipitation chance applies to this forecast period and can include rain or snow. The displayed temperature is a forecast high or low, not a current observation.','source-note');
    note.classList.add('nws-period-note');
  }
  function selectPeriod(index) {
    const buttons=[...content.querySelectorAll('.nws-period')];
    buttons.forEach((button,i)=>{button.classList.toggle('selected',i===index);button.setAttribute('aria-pressed',String(i===index));});
    renderSelected(current.periods[index]);
    content.querySelector('.nws-feature').setAttribute('aria-label',current.periods[index].name+' forecast');
    const announcement=content.querySelector('.nws-selection-announcement');
    if(announcement)announcement.textContent='Selected '+current.periods[index].name+': '+(current.periods[index].shortForecast||'forecast details above');
  }
  function renderHours(periods) {
    const block=element(content,'section',null,'nws-hourly');
    const head=element(block,'div',null,'nws-hourly-heading');element(head,'h4','The next 12 hours.');
    element(head,'span','HOURLY FORECAST / '+current.timeZone,'eyebrow');
    if(!periods?.length) {element(block,'p','Hourly guidance is unavailable right now. The period forecast above remains available.','muted');return;}
    const scroll=element(block,'div',null,'nws-hour-scroll');scroll.setAttribute('tabindex','0');scroll.setAttribute('role','region');scroll.setAttribute('aria-label','Hourly forecast; scroll horizontally for more hours');
    const hours=element(scroll,'div',null,'nws-hours');
    const temps=periods.map(temperature).filter(t=>t!==null),low=Math.min(...temps),high=Math.max(...temps);
    periods.forEach(period=>{
      const item=element(hours,'article',null,'nws-hour');
      element(item,'p',friendlyTime(period.startTime,current.timeZone,{hour:'numeric'}),'nws-hour-time');
      item.append(weatherIcon(period));
      const value=temperature(period);
      element(item,'strong',value===null?'—':value+'°');
      const indicator=element(item,'div',null,'nws-hour-indicator');indicator.setAttribute('aria-hidden','true');
      const bar=element(indicator,'span');bar.style.height=value===null?'0':(15+(value-low)/Math.max(1,high-low)*30)+'px';
      const pop=probability(period);element(item,'p',pop==null?'PoP unavailable':pop+'% precip.','nws-hour-pop');
      item.title=period.shortForecast||'';
    });
  }
  function renderForecast(data) {
    current=data;content.replaceChildren();content.hidden=false;
    const header=element(content,'div',null,'nws-place-heading');
    const name=element(header,'div');element(name,'p',data.isDefault?'CHARLOTTE / DEFAULT LOCATION':'YOUR LOCAL FORECAST','eyebrow');
    element(name,'h3',data.name);
    const source=element(header,'div',null,'nws-attribution');
    element(source,'span','NATIONAL WEATHER SERVICE');
    element(source,'p','Office '+data.office+' · Updated '+friendlyTime(data.updated,data.timeZone,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}));
    const age=Date.now()-Date.parse(data.updated);
    if(Number.isFinite(age)&&age>24*3600000) element(content,'p','The NWS update is more than 24 hours old. Forecast periods are still listed below; check the official source for newer guidance.','sunset-status sunset-stale');
    element(content,'div',null,'nws-feature');
    const announcement=element(content,'p',null,'sr-only nws-selection-announcement');announcement.setAttribute('aria-live','polite');
    const title=element(content,'div',null,'nws-period-heading');element(title,'h4','Day to night.');element(title,'p','Select a period to read the full forecast.','muted');
    const scroll=element(content,'div',null,'nws-period-scroll');
    const grid=element(scroll,'div',null,'nws-periods');grid.setAttribute('role','group');grid.setAttribute('aria-label','Choose a forecast period');
    data.periods.forEach((period,index)=>{
      const button=element(grid,'button',null,'nws-period');button.type='button';button.setAttribute('aria-pressed',String(index===0));
      element(button,'span',period.name,'nws-period-name');
      element(button,'small',period.isDaytime===true?'DAY / HIGH':period.isDaytime===false?'NIGHT / LOW':'FORECAST','nws-period-kind');
      button.append(weatherIcon(period));
      const value=temperature(period);element(button,'strong',value===null?'—':value+'°');
      element(button,'span',period.shortForecast||'Not supplied','nws-period-condition');
      const pop=probability(period);element(button,'small',pop==null?'Precip. chance not supplied':pop+'% precip.','nws-period-pop');
      button.addEventListener('click',()=>selectPeriod(index));
      button.addEventListener('keydown',event=>{
        const next=event.key==='ArrowRight'?Math.min(data.periods.length-1,index+1):event.key==='ArrowLeft'?Math.max(0,index-1):null;
        if(next!==null){event.preventDefault();grid.children[next].focus();selectPeriod(next);}
      });
    });
    selectPeriod(0);renderHours(data.hours);
    const footer=element(content,'div',null,'nws-footer');
    link(footer,'Full NWS forecast & alerts ↗',data.webURL);
    const sunset=new URL('../sunset/index.html',location.href);sunset.search=new URLSearchParams({lat:data.latitude,lon:data.longitude,place:data.name,tz:data.timeZone});sunset.hash='location-heading';
    link(footer,'Sunset for this location ↗',sunset.href);
    const refresh=element(footer,'button','Refresh NWS forecast ↻','text-link nws-refresh');refresh.type='button';
    refresh.addEventListener('click',()=>loadLocation({...data,isDefault:false},true));
    element(content,'p','Retrieved '+friendlyTime(data.retrievedAt,data.timeZone,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})+' · Forecast periods and wording supplied by the NWS. Weather symbols are simplified illustrations of those forecasts.','source-note');
  }
  async function loadLocation(point,refresh=false) {
    const id=++sequence;controller?.abort();controller=new AbortController();
    const signal=controller.signal;matches.replaceChildren();content.hidden=true;loading.hidden=false;
    status.textContent='Getting the official NWS forecast for '+point.name+'…';
    try {
      const {latitude,longitude}=point;
      if(!Number.isFinite(latitude)||!Number.isFinite(longitude)||latitude< -90||latitude>90||longitude< -180||longitude>180)throw new Error('Enter valid latitude, longitude coordinates.');
      const key=latitude.toFixed(4)+','+longitude.toFixed(4);
      const cached=memoryCache.get(key);
      if(!refresh&&cached&&Date.now()-cached.cachedAt<10*60000) {
        const periods=cached.data.periods.filter(period=>Date.parse(period.endTime)>Date.now());
        const hours=cached.data.hours.filter(period=>Date.parse(period.endTime)>Date.now());
        if(periods.length) {
          renderForecast({...cached.data,periods,hours,name:point.name,isDefault:point.isDefault});
          status.textContent='Showing the official NWS forecast for '+point.name+'.';loading.hidden=true;return;
        }
      }
      const metadata=await getJSON('https://api.weather.gov/points/'+key,signal);
      const props=metadata.properties;
      if(!props?.forecast)throw new Error('A standard NWS land forecast is not available here. Try a nearby city or open weather.gov.');
      const forecastURL=nwsURL(props.forecast);forecastURL.searchParams.set('units','us');
      const hourlyURL=props.forecastHourly?nwsURL(props.forecastHourly):null;
      if(hourlyURL)hourlyURL.searchParams.set('units','us');
      const feeds=await Promise.allSettled([getJSON(forecastURL,signal),hourlyURL?getJSON(hourlyURL,signal):Promise.reject(new Error('No hourly endpoint'))]);
      if(id!==sequence)return;
      if(feeds[0].status!=='fulfilled')throw feeds[0].reason;
      const forecast=feeds[0].value.properties;
      const periods=forecast?.periods?.filter(p=>Number.isFinite(Date.parse(p.startTime))&&Date.parse(p.endTime)>Date.now()).slice(0,14);
      if(!periods?.length)throw new Error('The NWS has not supplied unexpired forecast periods for this location. Please try again later.');
      const hourly=feeds[1].status==='fulfilled'?feeds[1].value.properties?.periods:[];
      const hours=(hourly||[]).filter(p=>Number.isFinite(Date.parse(p.startTime))&&Date.parse(p.endTime)>Date.now()).slice(0,12);
      const relative=props.relativeLocation?.properties;
      const name=point.name==='Your location'&&relative?.city?[relative.city,relative.state].filter(Boolean).join(', '):point.name;
      const timeZone=props.timeZone||point.timezone||'UTC';
      const webURL=new URL('https://forecast.weather.gov/MapClick.php');webURL.search=new URLSearchParams({lat:latitude,lon:longitude});
      const data={...point,name,timeZone,office:props.gridId||props.cwa||'not provided',periods,hours,
        updated:forecast.updateTime||forecast.generatedAt,retrievedAt:new Date().toISOString(),webURL:webURL.href};
      memoryCache.set(key,{cachedAt:Date.now(),data});
      if(memoryCache.size>12)memoryCache.delete(memoryCache.keys().next().value);
      renderForecast(data);status.textContent='Showing the official NWS forecast for '+name+'.';
    } catch(error) {
      if(id!==sequence)return;
      if(error.name==='AbortError')return;
      status.textContent=error.name==='TimeoutError'?'The forecast request timed out. Please try again or open weather.gov.':error.message||'The forecast could not be loaded. Please try again.';
      content.replaceChildren();
      const box=element(content,'div',null,'nws-unavailable');content.hidden=false;
      element(box,'h3','The forecast is temporarily out of reach.');
      element(box,'p','Try another location or check the official forecast directly. No substitute weather values are shown.');
      link(box,'Open National Weather Service ↗','https://www.weather.gov/');
    } finally {if(id===sequence)loading.hidden=true;}
  }
  form.addEventListener('submit',async event=>{
    event.preventDefault();controller?.abort();controller=new AbortController();const signal=controller.signal;
    const id=++sequence;matches.replaceChildren();content.hidden=true;loading.hidden=true;
    const query=input.value.trim();
    const coords=query.match(/^(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$/);
    if(coords)return loadLocation({name:query,latitude:Number(coords[1]),longitude:Number(coords[2])});
    if(query.length<2){status.textContent='Enter a city and state, ZIP code, or latitude, longitude.';return;}
    status.textContent='Finding your location…';
    try {
      const url=new URL('https://geocoding-api.open-meteo.com/v1/search');url.search=new URLSearchParams({name:query,count:6,language:'en',format:'json',countryCode:'US'});
      const response=await fetch(url,{signal:AbortSignal.any([signal,AbortSignal.timeout(15000)])});
      if(!response.ok)throw new Error('City search is temporarily unavailable. Try coordinates or “Use my location.”');
      const data=await response.json();if(id!==sequence)return;
      const points=(data.results||[]).filter(p=>p.country_code==='US');
      if(!points.length){status.textContent='No US location found. Try a city and state, ZIP code, or coordinates.';return;}
      status.textContent='Choose your location:';
      points.forEach(point=>{const name=[point.name,point.admin1].filter(Boolean).join(', ');const button=element(matches,'button',name,'button');button.type='button';button.addEventListener('click',()=>loadLocation({...point,name}));});
    } catch(error){if(id===sequence&&error.name!=='AbortError')status.textContent=error.name==='TimeoutError'?'Location search timed out. Try coordinates or “Use my location.”':error.message;}
  });
  section.querySelector('[data-nws-geolocate]').addEventListener('click',()=>{
    const id=++sequence;controller?.abort();matches.replaceChildren();loading.hidden=true;
    if(!navigator.geolocation){status.textContent='Your browser does not offer location access. Search for a city or ZIP code instead.';return;}
    status.textContent='Waiting for your browser’s location permission…';
    navigator.geolocation.getCurrentPosition(position=>{if(id===sequence)loadLocation({name:'Your location',latitude:position.coords.latitude,longitude:position.coords.longitude});},
      ()=>{if(id===sequence)status.textContent='Location access was unavailable. You can still search for a city or ZIP code.';},
      {enableHighAccuracy:false,timeout:12000,maximumAge:300000});
  });
  loadLocation({name:'Charlotte, NC',latitude:35.227,longitude:-80.843,isDefault:true});
}
