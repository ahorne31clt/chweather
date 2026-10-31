(() => {
  const $=id=>document.getElementById('ensemble-'+id),base=new URL('../generated/ensembles/latest.json',document.baseURI);
  let meta,active,index=0,serial=0,playing=false,timer,notice='',probe,pendingProbe;
  const params=new URLSearchParams(location.search);if(['refs','gefs'].includes(params.get('model')))$('model').value=params.get('model');
  function stop(){playing=false;clearTimeout(timer);$('play').textContent='Play';}
  function stamp(){return active?.frames[index]?.images[$('product').value];}
  async function show(){
    if(!active)return;const token=++serial,frame=active.frames[index],item=stamp();probe=null;pendingProbe=null;$('readout').hidden=true;$('image').hidden=true;$('message').hidden=false;$('message').textContent='Loading ensemble probability map…';$('download').setAttribute('aria-disabled','true');
    const product=active.products.find(p=>p.id===$('product').value);
    if(!item||!/^(refs|gefs)-\d{10}-f\d{3}-[a-z0-9]+\.png$/.test(item.image_filename)){$('message').textContent='Product unavailable for this ensemble.';return;}
    $('slider').value=index;$('hour').textContent='F'+String(frame.forecast_hour).padStart(3,'0');$('members').textContent=frame.member_count+' contributing members';$('run').textContent='Run '+active.model_run.replace('T',' ')+' / '+active.native_resolution;
    $('valid').textContent=(item.accumulation_hours?`6-HOUR WINDOW ${item.valid_start_utc.replace('T',' ')} → ${item.valid_end_utc.replace('T',' ')}`:`VALID ${item.valid_end_utc.replace('T',' ')} / instantaneous`)+' · '+item.probability_kind.toUpperCase();
    const old=Date.now()-Date.parse(active.model_run)>24*3600000;$('status').dataset.stale=old;
    $('status').textContent=(old?'OLDER MODEL RUN · ':'')+notice+product.description+' Published '+meta.generated_at_utc.replace('T',' ')+'.';
    const url=new URL(item.image_filename,base);url.searchParams.set('v',item.image_sha256);
    history.replaceState(null,'','?'+new URLSearchParams({model:active.id,product:product.id,hour:frame.forecast_hour}));
    try{$('image').src=url.href;await $('image').decode();if(token!==serial)return;$('image').alt=`${active.label} ${product.label}, ${frame.member_count} members, ${item.valid_start_utc} to ${item.valid_end_utc}; ${item.probability_kind} probability.`;$('image').hidden=false;$('message').hidden=true;$('download').href=url.href;$('download').setAttribute('aria-disabled','false');}
    catch{if(token===serial){$('message').textContent='The selected probability map is unavailable. Try Refresh.';stop();}}
    if(playing&&token===serial)timer=setTimeout(()=>{index=(index+1)%active.frames.length;show();},1000);
  }
  function selectModel(initial=false){
    stop();const target=active?.frames[index]?.valid_time_utc,oldProduct=$('product').value;
    active=meta.models.find(m=>m.id===$('model').value);if(!active)throw new Error('Ensemble unavailable');
    $('product').replaceChildren(...active.products.map(p=>{const o=document.createElement('option');o.value=p.id;o.textContent=p.label;return o;}));
    const product=initial?params.get('product'):oldProduct;if(active.products.some(p=>p.id===product))$('product').value=product;
    index=0;notice='';
    if(initial){const hour=Number(params.get('hour'));const found=active.frames.findIndex(f=>f.forecast_hour===hour);if(found>=0)index=found;}
    else if(target){index=active.frames.reduce((best,f,i)=>Math.abs(Date.parse(f.valid_time_utc)-Date.parse(target))<Math.abs(Date.parse(active.frames[best].valid_time_utc)-Date.parse(target))?i:best,0);if(active.frames[index].valid_time_utc!==target)notice='Nearest published UTC time selected; an exact match is unavailable. ';}
    $('slider').max=active.frames.length-1;for(const id of ['prev','play','next','slider'])$(id).disabled=false;show();
  }
  async function load(){stop();try{const response=await fetch(base,{cache:'no-store',signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error();const data=await response.json();if(data.schema_version!==1||!data.models?.length)throw new Error();meta=data;selectModel(!active);}catch{$('image').hidden=true;$('message').hidden=false;$('message').textContent='Published ensemble data is unavailable. Try Refresh or use the NOAA links in Guide.';}}
  $('model').addEventListener('change',()=>selectModel());$('product').addEventListener('change',()=>{stop();notice='';show();});$('slider').addEventListener('input',()=>{stop();index=Number($('slider').value);show();});
  const step=amount=>{stop();if(active){index=(index+amount+active.frames.length)%active.frames.length;show();}};
  $('prev').addEventListener('click',()=>step(-1));$('next').addEventListener('click',()=>step(1));$('play').addEventListener('click',()=>{if(playing)stop();else{playing=true;$('play').textContent='Pause';show();}});
  $('refresh').addEventListener('click',load);$('guide-open').addEventListener('click',()=>{stop();$('guide').showModal();});$('share').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(location.href);}catch{$('status').textContent='Copy the address bar to share this model, threshold and forecast time.';}});
  document.addEventListener('keydown',e=>{if(e.target.closest('input,select,button,a,dialog')||$('guide').open||!active)return;if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();step(e.key==='ArrowLeft'?-1:1);}else if(e.key===' '){e.preventDefault();$('play').click();}});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});load();
  async function readout(event){
    if($('image').hidden||!stamp()?.readout)return;
    const item=stamp().readout,token=serial;
    try{
      if(!probe){
        if(!pendingProbe)pendingProbe=(async()=>{
          if(!/^(refs|gefs)-\d{10}-f\d{3}-[a-z0-9]+\.bin\.gz$/.test(item.filename))throw new Error();
          const url=new URL(item.filename,base);url.searchParams.set('v',item.sha256);
          const response=await fetch(url,{signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error();
          const bytes=await response.arrayBuffer(),hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');if(hash!==item.sha256)throw new Error();
          const decoded=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
          if(decoded.byteLength!==item.width*item.height*2)throw new Error();return new DataView(decoded);
        })();
        const view=await pendingProbe;if(token!==serial)return;probe=view;
      }
      const rect=$('image').getBoundingClientRect(),scale=Math.min(rect.width/2000,rect.height/1125);
      const x=(event.clientX-rect.left-(rect.width-2000*scale)/2)/scale,y=(event.clientY-rect.top-(rect.height-1125*scale)/2)/scale;
      const col=Math.floor(x/5),row=Math.floor(y/5);
      if(col<0||row<0||col>=item.width||row>=item.height){$('readout').hidden=true;return;}
      const value=probe.getUint16((row*item.width+col)*2,true);if(value===item.missing){$('readout').hidden=true;return;}
      $('readout').textContent=`${(value/item.scale).toFixed(1)}% · ${stamp().probability_kind} / nearest sampled grid`;$('readout').hidden=false;
    }catch{if(token===serial){pendingProbe=null;$('readout').textContent='Numeric lookup unavailable';$('readout').hidden=false;}}
  }
  $('image').addEventListener('pointermove',readout);$('image').addEventListener('pointerdown',readout);$('image').addEventListener('pointerleave',()=>$('readout').hidden=true);
})();
