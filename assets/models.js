const modelStage=document.querySelector('#model-stage');
if(modelStage){
  const map=document.querySelector('#model-map'),message=document.querySelector('#model-message');
  const select=document.querySelector('#model-select'),range=document.querySelector('#model-range');
  const field=document.querySelector('#model-field'),readout=document.querySelector('#model-readout');
  const region=document.querySelector('#model-region'),loopStart=document.querySelector('#model-loop-start'),loopEnd=document.querySelector('#model-loop-end'),jump=document.querySelector('#model-jump');
  const initial=new URLSearchParams(location.search);
  let timeNotice='',runNotice='',fieldNotice='';
  const prev=document.querySelector('#model-prev'),next=document.querySelector('#model-next'),play=document.querySelector('#model-play');
  const note=document.querySelector('#model-note'),zone=document.querySelector('#model-zone');
  const hourLabel=document.querySelector('#model-hour'),validLabel=document.querySelector('#model-valid');
  const runLabel=document.querySelector('#model-run'),download=document.querySelector('#model-download');
  const speed=document.querySelector('#model-speed'),guide=document.querySelector('#model-guide');
  const base=new URL('../generated/models/latest.json',document.baseURI);
  let manifest,model,index=0,requestID=0,playing=false,timer,zoom=1,panX=0,panY=0,drag;
  const pendingImages=new Map();
  function formatTime(value,timezone='UTC'){
    return new Intl.DateTimeFormat('en-US',{timeZone:timezone,weekday:'short',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZoneName:'short'}).format(new Date(value));
  }
  function fileURL(frame){
    const image=frame.images?.[field.value]||(field.value==='precip'?frame:null);
    if(!image||!/^(gfs|hrrr|nam)-\d{10}-f\d{3}(-(temp2m|dewpoint2m|wind500|vort500|wind10|rh2m|mslp|sbcape))?\.png$/.test(image.image_filename))throw new Error('This field is not published for this model run.');
    const url=new URL(image.image_filename,base);url.searchParams.set('v',image.image_sha256);return url.href;
  }
  const smoothing=document.querySelector('#model-smoothing');
  let smoothingPreference=smoothing.value;
  const probe=new CHModelProbe(modelStage,map,readout);
  function loadReadouts(frame,id){
    const definition=manifest.products?.find(p=>p.id===field.value);
    smoothing.disabled=field.value==='precip';
    smoothing.value=smoothing.disabled?'off':smoothingPreference;
    probe.load(frame,field.value,definition);
    probe.mode=smoothing.disabled?'off':smoothing.value;
    if(probe.mode!=='off')probe.setMode(probe.mode);
    updateURL();
  }
  function samplePointer(event){probe.pointer(event);}
  smoothing.addEventListener('change',()=>{smoothingPreference=smoothing.value;probe.setMode(smoothing.value);updateURL();});
  download.addEventListener('click',event=>{
    if(probe.canvas.hidden)return;
    event.preventDefault();probe.canvas.toBlob(blob=>{if(!blob)return;const link=document.createElement('a'),url=URL.createObjectURL(blob);link.href=url;link.download=model.id+'-F'+model.frames[index].hour+'-'+field.value+'-smoothed.png';link.click();setTimeout(()=>URL.revokeObjectURL(url),30000);},'image/png');
  });
  function loadImage(url){
    if(pendingImages.has(url))return pendingImages.get(url);
    const promise=new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(new Error('This model frame could not be loaded. Try another forecast hour or check back later.'));image.src=url;});
    pendingImages.set(url,promise);
    if(pendingImages.size>8)pendingImages.delete(pendingImages.keys().next().value);
    promise.catch(()=>pendingImages.delete(url));return promise;
  }
  function displayMessage(text){message.replaceChildren();message.textContent=text;message.hidden=false;}
  function updateClock(){if(model?.frames[index]){const frame=model.frames[index];validLabel.textContent='Valid '+formatTime(frame.valid_time_utc,zone.value);range.setAttribute('aria-valuetext',`Forecast hour ${frame.hour}; ${formatTime(frame.valid_time_utc,zone.value)}`);}}
  function stop(){playing=false;clearTimeout(timer);play.textContent='Play';play.setAttribute('aria-label','Play forecast loop');play.setAttribute('aria-pressed','false');}
  function updateURL(){
    if(!model)return;const params=new URLSearchParams();
    params.set('model',model.id);params.set('field',field.value);params.set('hour',model.frames[index].hour);params.set('run',model.model_run);
    params.set('smooth',smoothing.value);params.set('region',region.value);params.set('zone',zone.value);params.set('from',model.frames[Number(loopStart.value)||0].hour);params.set('to',model.frames[Number(loopEnd.value)||0].hour);
    if(region.value==='custom'){const fit=Math.min(modelStage.clientWidth/2400,modelStage.clientHeight/1350);params.set('zoom',zoom.toFixed(2));params.set('cx',(1200-panX/(fit*zoom)).toFixed(1));params.set('cy',(675-panY/(fit*zoom)).toFixed(1));}
    history.replaceState(null,'',location.pathname+'?'+params.toString());
  }
  function applyRegion(){
    const preset=model?.regions?.find(r=>r.id===region.value);
    zoom=preset?.zoom||1;
    const fit=Math.min(modelStage.clientWidth/2400,modelStage.clientHeight/1350);
    panX=preset?-(preset.x-1200)*fit*zoom:0;panY=preset?-(preset.y-675)*fit*zoom:0;
    transformMap();updateURL();
  }
  function customView(){region.value='custom';transformMap();updateURL();}
  function pinnedLegend(){
    const box=document.querySelector('#model-pinned-legend'),definition=manifest?.products?.find(p=>p.id===field.value);
    box.replaceChildren();box.hidden=zoom<=1||!definition;if(box.hidden)return;
    const heading=document.createElement('strong');heading.textContent=definition.label+(definition.unit?' / '+definition.unit:'');box.append(heading);
    if(definition.swatches){
      const bar=document.createElement('div');bar.className='model-legend-swatches';
      for(const color of definition.swatches){const swatch=document.createElement('span');swatch.style.backgroundColor=color;bar.append(swatch);}box.append(bar);
      const labels=document.createElement('div');labels.className='model-legend-labels';const levels=definition.levels;
      for(const value of [levels[0],levels[Math.floor(levels.length/2)],levels.at(-1)]){const label=document.createElement('span');label.textContent=value;labels.append(label);}box.append(labels);
    }else if(definition.legend){
      const labels=document.createElement('div');labels.className='model-legend-types';
      for(const item of definition.legend){const label=document.createElement('span'),color=document.createElement('i');color.style.backgroundColor=item.color;label.append(color,document.createTextNode(item.label));labels.append(label);}box.append(labels);
    }
  }
  function nextLoopIndex(){const a=Number(loopStart.value),b=Number(loopEnd.value);return index<a||index>=b?a:index+1;}
  function transformMap(){
    const maxX=modelStage.clientWidth*(zoom-1)/2,maxY=modelStage.clientHeight*(zoom-1)/2;
    panX=Math.max(-maxX,Math.min(maxX,panX));panY=Math.max(-maxY,Math.min(maxY,panY));
    map.style.transform=`translate(${panX}px,${panY}px) scale(${zoom})`;
    modelStage.classList.toggle('is-zoomed',zoom>1);document.querySelector('#model-zoom-label').textContent=zoom.toFixed(1)+'×';
    pinnedLegend();probe.setView({zoom,panX,panY});
  }
  async function showFrame(target){
    if(!model)return;
    index=Math.max(0,Math.min(model.frames.length-1,target));const frame=model.frames[index];const id=++requestID;
    range.value=index;hourLabel.textContent='F'+String(frame.hour).padStart(3,'0');
    jump.value=index;updateURL();
    range.setAttribute('aria-valuetext',`Forecast hour ${frame.hour}; ${formatTime(frame.valid_time_utc,zone.value)}`);
    modelStage.setAttribute('aria-busy','true');map.hidden=true;download.setAttribute('aria-disabled','true');readout.hidden=true;probe.hideSmooth();
    displayMessage(`Loading ${model.name} F${String(frame.hour).padStart(3,'0')}…`);
    try{
      const url=fileURL(frame);await loadImage(url);if(id!==requestID)return;
      const label=field.selectedOptions[0].textContent;
      map.src=url;map.alt=`${model.name}, ${label}, run ${model.model_run}, ${frame.hour===0?'model analysis':`forecast hour ${frame.hour}`}, valid ${frame.valid_time_utc}. Temperatures/dewpoints in Fahrenheit; upper-air wind speed in knots, heights in decameters, absolute vorticity in 10^-5 per second. Precipitation maps use solid pressure and dashed thickness contours, with H/L pressure centers.`;
      document.querySelector('.model-product').textContent=label.toUpperCase();
      pinnedLegend();
      map.hidden=false;message.hidden=true;modelStage.setAttribute('aria-busy','false');updateClock();
      download.href=url;download.setAttribute('aria-disabled','false');
      loadReadouts(frame,id);
      const age=Date.now()-Date.parse(model.model_run);
      const stale=age>24*3600000?'OLDER RUN: ':'';
      const horizon=model.id==='hrrr'&&model.requested_end_hour>model.frames.at(-1).hour?' · 18h fallback; extended run unavailable':'';
      note.textContent=runNotice+fieldNotice+timeNotice+stale+model.name+' · '+(frame.hour===0?'F000 model analysis':'forecast guidance')+' · '+model.native_resolution+' · '+model.frames.length+' published hours'+horizon+' · Generated '+formatTime(model.generated_at_utc||manifest.generated_at_utc)+' · Arrow keys step; space plays.';
      // Fetch only neighbors, rather than loading dozens of large PNGs at once.
      for(const neighbor of [index+1,index-1])if(model.frames[neighbor])loadImage(fileURL(model.frames[neighbor])).catch(()=>{});
      if(playing)timer=setTimeout(()=>showFrame(nextLoopIndex()),Number(speed.value));
    }catch(error){if(id!==requestID)return;stop();map.hidden=true;download.setAttribute('aria-disabled','true');modelStage.setAttribute('aria-busy','false');displayMessage(error.message);}
  }
  function selectModel(id,targetTime){
    const wanted=targetTime??(model?Date.parse(model.frames[index].valid_time_utc):null),oldRegion=region.value;
    stop();model=manifest.models.find(item=>item.id===id&&item.status==='available');
    if(!model)return;
    for(const option of field.options)option.disabled=!model.frames.every(frame=>frame.images?.[option.value]||(!frame.images&&option.value==='precip'&&model.id!=='nam'));
    fieldNotice='';if(field.selectedOptions[0]?.disabled){field.value=Array.from(field.options).find(option=>!option.disabled).value;fieldNotice='Previous parameter unavailable; '+field.selectedOptions[0].textContent+' shown · ';}
    select.value=id;index=0;range.min=0;range.max=model.frames.length-1;range.value=0;
    if(Number.isFinite(wanted))index=model.frames.reduce((best,frame,i)=>Math.abs(Date.parse(frame.valid_time_utc)-wanted)<Math.abs(Date.parse(model.frames[best].valid_time_utc)-wanted)?i:best,0);
    timeNotice=Number.isFinite(wanted)&&Date.parse(model.frames[index].valid_time_utc)!==wanted?'Nearest published valid time · ':'';
    for(const control of [loopStart,loopEnd,jump]){control.replaceChildren();model.frames.forEach((frame,i)=>{const option=document.createElement('option');option.value=i;option.textContent='F'+String(frame.hour).padStart(3,'0')+' · '+formatTime(frame.valid_time_utc);control.append(option);});}
    loopStart.value=0;loopEnd.value=model.frames.length-1;
    region.replaceChildren();for(const preset of model.regions||[{id:'conus',label:'CONUS'}]){const option=document.createElement('option');option.value=preset.id;option.textContent=preset.label;region.append(option);}
    const custom=document.createElement('option');custom.value='custom';custom.textContent='Custom zoom';region.append(custom);
    region.value=Array.from(region.options).some(o=>o.value===oldRegion)?oldRegion:'conus';
    modelStage.dataset.modelRun=model.model_run;modelStage.dataset.modelId=model.id;
    modelStage.dataset.modelHours=JSON.stringify(model.frames.map(frame=>frame.hour));
    document.querySelector('#airport-open').disabled=model.id==='nam';
    document.querySelector('#airport-open').title=model.id==='nam'?'Airport rate meteograms are available for GFS and HRRR.':'';
    window.dispatchEvent(new CustomEvent('chweather:model-change',{detail:{id:model.id,run:model.model_run}}));
    runLabel.textContent='Init '+formatTime(model.model_run)+' · '+model.native_resolution;
    document.querySelector('#model-end').textContent='F'+String(model.frames.at(-1).hour).padStart(3,'0');
    applyRegion();showFrame(index);
  }
  function step(delta){stop();timeNotice='';const a=Number(loopStart.value),b=Number(loopEnd.value);showFrame(index<a||index>b?(delta>0?a:b):index+delta>b?a:index+delta<a?b:index+delta);}
  select.addEventListener('change',()=>{runNotice='';selectModel(select.value);});
  field.addEventListener('change',()=>{stop();fieldNotice='';showFrame(index);});
  range.addEventListener('input',()=>{stop();timeNotice='';showFrame(Number(range.value));});
  prev.addEventListener('click',()=>step(-1));next.addEventListener('click',()=>step(1));
  play.addEventListener('click',()=>{
    if(!model)return;if(playing){stop();return;}
    playing=true;play.textContent='Pause';play.setAttribute('aria-label','Pause forecast loop');play.setAttribute('aria-pressed','true');
    showFrame(nextLoopIndex());
  });
  speed.addEventListener('change',()=>{if(playing){clearTimeout(timer);showFrame(index);}});
  zone.addEventListener('change',()=>{updateClock();updateURL();});
  region.addEventListener('change',applyRegion);
  document.querySelector('#model-zoom-in').addEventListener('click',()=>{zoom=Math.min(4,zoom+.5);customView();});
  document.querySelector('#model-zoom-out').addEventListener('click',()=>{zoom=Math.max(1,zoom-.5);customView();});
  document.querySelector('#model-reset').addEventListener('click',()=>{region.value='conus';applyRegion();});
  for(const control of [loopStart,loopEnd])control.addEventListener('change',()=>{stop();if(Number(loopStart.value)>Number(loopEnd.value)){if(control===loopStart)loopEnd.value=loopStart.value;else loopStart.value=loopEnd.value;}updateURL();});
  document.querySelector('#model-jump-go').addEventListener('click',()=>{stop();guide.close();showFrame(Number(jump.value));});
  document.querySelector('#model-share').addEventListener('click',async()=>{updateURL();const status=document.querySelector('#model-tool-status');try{await navigator.clipboard.writeText(location.href);status.textContent='Link copied. It includes this model, parameter, region, hour, and loop range.';}catch{status.textContent='Copy the URL from your browser address bar to share this view.';}});
  modelStage.addEventListener('pointerdown',event=>{
    if(zoom<=1||event.target.closest('button'))return;
    drag={x:event.clientX,y:event.clientY,panX,panY};modelStage.setPointerCapture(event.pointerId);modelStage.classList.add('is-dragging');
  });
  modelStage.addEventListener('pointermove',event=>{if(!drag)return;panX=drag.panX+event.clientX-drag.x;panY=drag.panY+event.clientY-drag.y;transformMap();});
  modelStage.addEventListener('pointermove',samplePointer);
  modelStage.addEventListener('click',samplePointer);
  for(const type of ['pointerup','pointercancel'])modelStage.addEventListener(type,()=>{if(drag)customView();drag=null;modelStage.classList.remove('is-dragging');});
  window.addEventListener('resize',()=>{probe.lastPointer=null;if(region.value==='custom')transformMap();else applyRegion();});
  document.querySelector('#model-info').addEventListener('click',()=>{stop();guide.showModal();});
  document.querySelector('#model-fullscreen').addEventListener('click',async()=>{
    try{if(document.fullscreenElement)await document.exitFullscreen();else await document.querySelector('.model-shell').requestFullscreen();}
    catch{note.textContent='Fullscreen is unavailable in this browser. The map is already fitted to this window.';}
  });
  document.addEventListener('keydown',event=>{
    if(!model||guide.open||document.querySelector('#airport-dialog')?.open||event.altKey||event.ctrlKey||event.metaKey||event.target.matches('input,select,textarea')||event.target.isContentEditable)return;
    if(event.key==='ArrowLeft'){event.preventDefault();step(-1);}
    else if(event.key==='ArrowRight'){event.preventDefault();step(1);}
    else if(event.key==='Home'){event.preventDefault();stop();showFrame(Number(loopStart.value));}
    else if(event.key==='End'){event.preventDefault();stop();showFrame(Number(loopEnd.value));}
    else if(event.code==='Space'&&!event.target.closest('button,a')){event.preventDefault();play.click();}
  });
  let checkingUpdate=false;
  async function refreshPublishedModels(){
    if(checkingUpdate||document.hidden||!manifest||!model||guide.open||document.querySelector('#airport-dialog')?.open)return;
    checkingUpdate=true;
    const status=document.querySelector('#model-tool-status');
    try{
      const response=await fetch(base,{cache:'no-store',signal:AbortSignal.timeout(15000)});
      if(!response.ok)throw new Error('The latest published run could not be checked. Current run retained.');
      const updated=await response.json();
      if(!Number.isFinite(Date.parse(updated.generated_at_utc)))throw new Error('Updated publication time could not be verified. Current run retained.');
      if(Date.parse(updated.generated_at_utc)<Date.parse(manifest.generated_at_utc))return;
      const available=updated.models?.filter(item=>['gfs','hrrr','nam'].includes(item.id)&&item.status==='available'&&item.frames?.length);
      if(!available?.length||available.some(item=>!Number.isFinite(Date.parse(item.model_run))||item.frames.some(frame=>!Number.isInteger(frame.hour)||!Number.isFinite(Date.parse(frame.valid_time_utc)))))throw new Error('Updated model metadata could not be verified. Current run retained.');
      if(updated.generated_at_utc===manifest.generated_at_utc&&available.every(item=>manifest.models.some(old=>old.id===item.id&&old.model_run===item.model_run)))return;
      const wanted=Date.parse(model.frames[index].valid_time_utc),nextModel=available.find(item=>item.id===model.id)||available[0];
      stop();pendingImages.clear();manifest=updated;runNotice='Updated automatically to the latest published guidance · ';
      for(const option of select.options)option.disabled=!available.some(item=>item.id===option.value);
      window.dispatchEvent(new Event('chweather:model-manifest-update'));
      selectModel(nextModel.id,wanted);
      status.textContent='New model publication loaded automatically. Checking for updates every 5 minutes.';
    }catch(error){status.textContent=error.message||'Update check failed; the displayed run is retained.';}
    finally{checkingUpdate=false;}
  }
  setInterval(refreshPublishedModels,5*60*1000);
  window.addEventListener('online',refreshPublishedModels);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else refreshPublishedModels();});
  window.addEventListener('chweather:pause-model',stop);
  (async()=>{
    try{
      const response=await fetch(base,{cache:'no-store',signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error('Model guidance is temporarily unavailable. Please check back after the next update.');
      manifest=await response.json();
      const available=manifest.models?.filter(item=>['gfs','hrrr','nam'].includes(item.id)&&item.status==='available'&&item.frames?.length);
      if(!available?.length)throw new Error('No model cycle is available right now. Please check back later.');
      for(const item of available){if(!Number.isFinite(Date.parse(item.model_run))||item.frames.some(frame=>!Number.isInteger(frame.hour)||!Number.isFinite(Date.parse(frame.valid_time_utc))))throw new Error('Model metadata could not be read. Please check back later.');}
      for(const option of select.options){const item=available.find(item=>item.id===option.value);option.disabled=!item;if(!item)option.textContent=option.value.toUpperCase()+' unavailable';}
      for(const control of [select,field,range,prev,next,play])control.disabled=false;
      if(['off','smooth'].includes(initial.get('smooth'))){smoothing.value=initial.get('smooth');smoothingPreference=smoothing.value;}
      if(Array.from(field.options).some(o=>o.value===initial.get('field')))field.value=initial.get('field');
      if(['UTC','America/New_York'].includes(initial.get('zone')))zone.value=initial.get('zone');
      const first=available.find(item=>item.id===initial.get('model'))||available.find(item=>item.id==='gfs')||available[0];
      if(initial.get('run')&&initial.get('run')!==first.model_run)runNotice='Requested run is no longer published; latest run shown · ';
      selectModel(first.id,null);
      const wantedHour=Number(initial.get('hour'));if(initial.has('hour')&&Number.isFinite(wantedHour))index=model.frames.reduce((best,frame,i)=>Math.abs(frame.hour-wantedHour)<Math.abs(model.frames[best].hour-wantedHour)?i:best,0);
      for(const [param,control] of [['from',loopStart],['to',loopEnd]])if(initial.has(param)){const hour=Number(initial.get(param)),i=model.frames.findIndex(f=>f.hour===hour);if(i>=0)control.value=i;}
      if(Number(loopStart.value)>Number(loopEnd.value))loopStart.value=loopEnd.value;
      if(Array.from(region.options).some(o=>o.value===initial.get('region')))region.value=initial.get('region');
      if(region.value==='custom'){
        const z=Number(initial.get('zoom')),cx=Number(initial.get('cx')),cy=Number(initial.get('cy')),fit=Math.min(modelStage.clientWidth/2400,modelStage.clientHeight/1350);
        if(z>=1&&z<=4&&cx>=0&&cx<=2400&&cy>=0&&cy<=1350){zoom=z;panX=-(cx-1200)*fit*zoom;panY=-(cy-675)*fit*zoom;transformMap();}else{region.value='conus';applyRegion();}
      }else applyRegion();
      showFrame(index);
    }catch(error){map.hidden=true;modelStage.setAttribute('aria-busy','false');displayMessage(error.message||'Model guidance could not be loaded. Please check back later.');}
  })();
}
