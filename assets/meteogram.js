(() => {
  const dialog=document.querySelector('#airport-dialog');if(!dialog)return;
  const status=document.querySelector('#airport-status'),content=document.querySelector('#airport-content');
  const query=document.querySelector('#airport-query'),results=document.querySelector('#airport-results');
  const choice=document.querySelector('#airport-model'),zone=document.querySelector('#airport-zone');
  const svg=document.querySelector('#airport-chart'),slider=document.querySelector('#airport-hour');
  const base=new URL('../generated/models/airports/latest.json',document.baseURI);
  let metadata,catalog,selectedAirport,activeModel,series=[],selectedIndex=0,request=0;
  const buckets=new Map();
  window.addEventListener('chweather:model-manifest-update',()=>{metadata=null;catalog=null;selectedAirport=undefined;activeModel=null;series=[];buckets.clear();content.hidden=true;});
  function time(value){return new Intl.DateTimeFormat('en-US',{timeZone:zone.value,month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(new Date(value));}
  async function bytes(url,hash){
    const response=await fetch(url,{signal:AbortSignal.timeout(20000)});if(!response.ok)throw new Error('Airport guidance is temporarily unavailable. Please try again later.');
    const buffer=await response.arrayBuffer();
    if(hash&&crypto.subtle){const found=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer)),n=>n.toString(16).padStart(2,'0')).join('');if(found!==hash)throw new Error('The airport data could not be verified. Please refresh.');}
    return buffer;
  }
  async function initialize(){
    if(metadata&&catalog)return;
    const url=new URL(base);url.searchParams.set('t',Date.now());metadata=JSON.parse(new TextDecoder().decode(await bytes(url)));
    if(!metadata.models?.length||metadata.catalog_count<1000)throw new Error('Airport model data is not available yet.');
    const catalogURL=new URL(metadata.catalog_filename,base);catalogURL.searchParams.set('v',metadata.catalog_sha256);
    catalog=JSON.parse(new TextDecoder().decode(await bytes(catalogURL,metadata.catalog_sha256)));
    if(catalog.length!==metadata.catalog_count)throw new Error('The airport catalog could not be verified.');
    catalog.forEach(a=>a.search=[a.id,a.icao,a.iata,a.local,a.name,a.city,a.state].join(' ').toLowerCase());
    for(const option of choice.options)option.disabled=!metadata.models.some(m=>m.id===option.value);
  }
  function codes(a){return [a.icao||a.id,a.iata].filter(Boolean).join(' / ');}
  function matches(text){
    const q=text.trim().toLowerCase();if(q.length<2)return [];
    return catalog.map((a,index)=>({a,index,rank:[a.id,a.icao,a.iata,a.local].some(c=>c?.toLowerCase()===q)?0:a.search.startsWith(q)?1:a.search.includes(q)?2:9}))
      .filter(a=>a.rank<9).sort((a,b)=>a.rank-b.rank||(a.a.type==='large_airport'?-1:0)-(b.a.type==='large_airport'?-1:0)||a.a.name.localeCompare(b.a.name)).slice(0,10);
  }
  function suggestions(){
    results.replaceChildren();if(!catalog)return;
    for(const hit of matches(query.value)){
      const li=document.createElement('li'),button=document.createElement('button');button.type='button';
      const code=document.createElement('strong');code.textContent=codes(hit.a);button.append(code,document.createTextNode(hit.a.name));
      const detail=document.createElement('small');detail.textContent=[hit.a.city,hit.a.state].filter(Boolean).join(', ');button.append(detail);
      button.addEventListener('click',()=>chooseAirport(hit.index));li.append(button);results.append(li);
    }
  }
  async function chooseAirport(index){
    selectedAirport=index;query.value=catalog[index].icao||catalog[index].id;results.replaceChildren();await loadSeries();
  }
  async function loadSeries(){
    if(selectedAirport===undefined||!metadata)return;
    const id=++request;content.hidden=true;status.textContent='Loading airport meteogram…';
    try{
      const model=metadata.models.find(m=>m.id===choice.value);
      const map=document.querySelector('#model-stage');
      const hours=JSON.parse(map.dataset.modelHours||'[]');
      if(!model||model.model_run!==map.dataset.modelRun||model.id!==map.dataset.modelId||hours.length!==model.hours.length||hours.some((hour,i)=>hour!==model.hours[i]))throw new Error('Airport charts for this model run are still updating. Please check back after the next publication.');
      const bucket=model.chunks.find(c=>selectedAirport>=c.start&&selectedAirport<c.start+c.count);
      if(!bucket||!/^((gfs|hrrr)-\d{10}-airports-\d{4}\.bin)$/.test(bucket.filename))throw new Error('This airport is not available in the selected model.');
      let buffer=buckets.get(bucket.filename);
      if(!buffer){const url=new URL(bucket.filename,base);url.searchParams.set('v',bucket.sha256);buffer=await bytes(url,bucket.sha256);buckets.set(bucket.filename,buffer);if(buckets.size>6)buckets.delete(buckets.keys().next().value);}
      if(buffer.byteLength!==bucket.count*model.times.length*3*4)throw new Error('Airport forecast data has an unexpected size.');
      if(id!==request)return;
      const view=new DataView(buffer),offset=(selectedAirport-bucket.start)*model.times.length*12;
      series=model.times.map((valid,i)=>({valid,timestamp:Date.parse(valid),hour:model.hours[i],
        temp:view.getFloat32(offset+i*12,true),wind:view.getFloat32(offset+i*12+4,true),rate:view.getFloat32(offset+i*12+8,true)/25.4}));
      if(!series.some(p=>[p.temp,p.wind,p.rate].every(Number.isFinite)))throw new Error('The selected airport lies outside this model’s usable grid.');
      activeModel=model;selectedIndex=0;slider.min=0;slider.max=series.length-1;slider.value=0;
      document.querySelector('#airport-name').textContent=codes(catalog[selectedAirport])+' · '+catalog[selectedAirport].name;
      document.querySelector('#airport-run').textContent=model.name+' · Init '+time(model.model_run)+' · '+model.native_resolution+' · F000–F'+String(model.hours.at(-1)).padStart(3,'0');
      content.hidden=false;status.textContent='Move over the chart, tap a forecast time, or use the time slider. Precipitation bars show instantaneous rate.';
      draw();selectTime(0);
    }catch(error){if(id===request){content.hidden=true;status.textContent=error.message;}}
  }
  const ns='http://www.w3.org/2000/svg';
  function add(tag,attrs={},text){const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);if(text!==undefined)el.textContent=text;svg.append(el);return el;}
  const left=75,right=1080,top=68,rowHeight=150,plotHeight=109;
  function x(index){return series.length===1?(left+right)/2:left+(series[index].timestamp-series[0].timestamp)/(series.at(-1).timestamp-series[0].timestamp)*(right-left);}
  function draw(){
    svg.replaceChildren();add('rect',{width:1120,height:630,fill:'#151c18'});
    add('text',{x:24,y:26,fill:'#E8EBE8','font-size':16,'font-weight':700},'CH WEATHER  /  '+codes(catalog[selectedAirport])+'  /  '+activeModel.name+' METEOGRAM');
    add('text',{x:24,y:45,fill:'#9FB4AC','font-size':10},'INIT '+time(activeModel.model_run)+' · Nearest model grid point · '+catalog[selectedAirport].name);
    const panels=[{key:'temp',name:'2 M TEMPERATURE / °F',color:'#76BA94'},
      {key:'wind',name:'10 M SUSTAINED WIND / kt',color:'#C19244'},
      {key:'rate',name:'INSTANTANEOUS PRECIP RATE / in/hr',color:'#72B6DD'}];
    panels.forEach((panel,r)=>{
      const start=top+r*rowHeight,values=series.map(p=>p[panel.key]).filter(Number.isFinite);
      const min=panel.key==='temp'?Math.floor((Math.min(...values)-5)/10)*10:0;
      const max=panel.key==='temp'?Math.ceil((Math.max(...values)+5)/10)*10:panel.key==='wind'?Math.max(20,Math.ceil((Math.max(...values)+3)/10)*10):Math.max(.05,Math.ceil(Math.max(...values)*20)/20);
      const y=value=>start+plotHeight-(value-min)/(max-min)*plotHeight;
      add('text',{x:left,y:start-10,fill:panel.color,'font-size':11,'font-weight':700},panel.name);
      for(let tick=0;tick<=4;tick++){
        const value=min+(max-min)*tick/4,py=y(value);
        add('line',{x1:left,x2:right,y1:py,y2:py,stroke:'#748c7c','stroke-opacity':.2,'stroke-width':.7});
        add('text',{x:left-10,y:py+4,fill:'#9FB4AC','text-anchor':'end','font-size':10},panel.key==='rate'?value.toFixed(2):value.toFixed(0));
      }
      if(panel.key==='temp'&&min<32&&max>32)add('line',{x1:left,x2:right,y1:y(32),y2:y(32),stroke:'#C9DBD0','stroke-opacity':.5,'stroke-dasharray':'4 5'});
      if(panel.key==='rate'){
        const width=Math.min(17,(right-left)/Math.max(1,series.length-1)*.65);
        series.forEach((p,i)=>{if(Number.isFinite(p.rate)&&p.rate>0)add('rect',{x:x(i)-width/2,y:y(p.rate),width,height:Math.max(.5,y(0)-y(p.rate)),fill:panel.color,opacity:.85});});
      }else{
        let path='',open=false;series.forEach((p,i)=>{if(!Number.isFinite(p[panel.key])){open=false;return;}path+=(open?' L':' M')+x(i).toFixed(2)+' '+y(p[panel.key]).toFixed(2);open=true;});
        add('path',{d:path,fill:'none',stroke:panel.color,'stroke-width':2.2,'stroke-linejoin':'round'});
      }
      for(let tick=0;tick<=6;tick++){
        const i=Math.round((series.length-1)*tick/6),px=x(i);
        add('line',{x1:px,x2:px,y1:start,y2:start+plotHeight,stroke:'#748c7c','stroke-opacity':.15,'stroke-width':.7});
        if(r===2)add('text',{x:px,y:start+plotHeight+20,fill:'#9FB4AC','font-size':9,'text-anchor':tick===0?'start':tick===6?'end':'middle'},time(series[i].valid));
      }
    });
    add('line',{id:'airport-crosshair',x1:left,x2:left,y1:top-4,y2:top+2*rowHeight+plotHeight,stroke:'#E8EBE8','stroke-width':1,'stroke-dasharray':'4 3','pointer-events':'none'});
    add('text',{id:'airport-svg-readout',x:left,y:548,fill:'#E8EBE8','font-size':12});
    add('text',{x:24,y:592,fill:'#9FB4AC','font-size':10},'NOAA/NCEP model guidance · Airport coordinates: OurAirports · CH Weather / Christopher Horne');
    add('text',{x:24,y:612,fill:'#9FB4AC','font-size':10},'Precipitation is a rate, not accumulation or probability. Wind is sustained, not gusts. Not an observation or a TAF.');
  }
  function selectTime(index){
    if(!series.length)return;selectedIndex=Math.max(0,Math.min(series.length-1,index));slider.value=selectedIndex;const p=series[selectedIndex];
    const label='F'+String(p.hour).padStart(3,'0')+' · '+time(p.valid);document.querySelector('#airport-time').textContent=label;slider.setAttribute('aria-valuetext',label);
    document.querySelector('#airport-temp').textContent=Number.isFinite(p.temp)?p.temp.toFixed(1)+'°F':'Unavailable';
    document.querySelector('#airport-wind').textContent=Number.isFinite(p.wind)?p.wind.toFixed(1)+' kt':'Unavailable';
    document.querySelector('#airport-precip').textContent=Number.isFinite(p.rate)?p.rate.toFixed(3)+' in/hr':'Unavailable';
    const detail=document.querySelector('#airport-svg-readout');if(detail)detail.textContent=label+'   |   '+document.querySelector('#airport-temp').textContent+'   |   '+document.querySelector('#airport-wind').textContent+' sustained   |   '+document.querySelector('#airport-precip').textContent;
    const line=document.querySelector('#airport-crosshair');line?.setAttribute('x1',x(selectedIndex));line?.setAttribute('x2',x(selectedIndex));
  }
  function chartPointer(event){
    if(!series.length)return;const rect=svg.getBoundingClientRect(),px=(event.clientX-rect.left)*1120/rect.width;
    if(px<left||px>right)return;let nearest=0;for(let i=1;i<series.length;i++)if(Math.abs(x(i)-px)<Math.abs(x(nearest)-px))nearest=i;selectTime(nearest);
  }
  svg.addEventListener('pointermove',chartPointer);svg.addEventListener('click',chartPointer);
  slider.addEventListener('input',()=>selectTime(Number(slider.value)));
  query.addEventListener('input',suggestions);
  query.addEventListener('keydown',event=>{if(event.key==='ArrowDown'){event.preventDefault();results.querySelector('button')?.focus();}});
  document.querySelector('#airport-search').addEventListener('submit',event=>{
    event.preventDefault();if(!catalog)return;
    const exact=matches(query.value).find(hit=>hit.rank===0);
    if(exact)chooseAirport(exact.index);else{suggestions();status.textContent=results.children.length?'Select an airport from the results below.':'No airport found. Try a CONUS ICAO/IATA code, airport name, or city.';}
  });
  choice.addEventListener('change',()=>{
    const map=document.querySelector('#model-select');map.value=choice.value;map.dispatchEvent(new Event('change',{bubbles:true}));
  });
  zone.addEventListener('change',()=>{if(activeModel){draw();selectTime(selectedIndex);document.querySelector('#airport-run').textContent=activeModel.name+' · Init '+time(activeModel.model_run)+' · '+activeModel.native_resolution;}});
  window.addEventListener('chweather:model-change',event=>{if(dialog.open){choice.value=event.detail.id;loadSeries();}});
  document.querySelector('#airport-open').addEventListener('click',async()=>{
    window.dispatchEvent(new Event('chweather:pause-model'));dialog.showModal();status.textContent='Loading airport catalog and model guidance…';
    choice.value=document.querySelector('#model-select').value;zone.value=document.querySelector('#model-zone').value;
    try{await initialize();if(!dialog.open)return;if(selectedAirport===undefined){const index=catalog.findIndex(a=>a.icao==='KCLT'||a.id==='KCLT');if(index>=0)await chooseAirport(index);else status.textContent='Search for a CONUS airport to create a meteogram.';}else await loadSeries();}
    catch(error){status.textContent=error.message;}
  });
  dialog.addEventListener('close',()=>{request++;});
  document.querySelector('#airport-map-hour').addEventListener('click',()=>{const range=document.querySelector('#model-range');range.value=selectedIndex;range.dispatchEvent(new Event('input',{bubbles:true}));dialog.close();});
  function save(blob,extension){const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download='CHWeather_'+catalog[selectedAirport].id+'_'+activeModel.name+'_'+activeModel.model_run.replace(/[:\-]/g,'').replace('T','_')+'.'+extension;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
  document.querySelector('#airport-csv').addEventListener('click',()=>{
    const quote=value=>'"'+String(value).replaceAll('"','""')+'"';
    const rows=[['airport','model','model_run_utc','valid_utc','forecast_hour','temperature_f','wind10_kt','precipitation_rate_in_hr'],...series.map(p=>[catalog[selectedAirport].id,activeModel.name,activeModel.model_run,p.valid,p.hour,...[p.temp,p.wind,p.rate].map(v=>Number.isFinite(v)?v:'')])];
    save(new Blob([rows.map(row=>row.map(quote).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),'csv');
  });
  document.querySelector('#airport-png').addEventListener('click',async()=>{
    try{const source=new XMLSerializer().serializeToString(svg),url=URL.createObjectURL(new Blob([source],{type:'image/svg+xml'}));
      const image=new Image();try{await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=url;});const canvas=document.createElement('canvas');canvas.width=2240;canvas.height=1260;canvas.getContext('2d').drawImage(image,0,0,2240,1260);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw new Error();save(blob,'png');}finally{URL.revokeObjectURL(url);}
    }catch{status.textContent='The PNG could not be exported in this browser. CSV download is still available.';}
  });
})();
