/* Timestamped NOAA imagery only; no inferred frames, forecast data or credentials. */
(() => {
  const $=id=>document.getElementById('sat-'+id);
  const image=$('image'),stage=document.querySelector('.sat-stage'),stamp=document.querySelector('.sat-stamp');
  const choices=['platform','sector','product','length'];
  let frames=[],index=0,epoch=0,request,playing=false,timer,zoom=1,panX=0,panY=0,drag,frameSerial=0;
  const cache=new Map();
  const params=new URLSearchParams(location.search);
  for(const name of [...choices,'zone'])if([...$(name).options].some(o=>o.value===params.get(name)))$(name).value=params.get(name);
  function configuration(){return Object.fromEntries(choices.map(k=>[k,$(k).value]));}
  function sourceURL(config=configuration()){
    const url=new URL('https://www.star.nesdis.noaa.gov/GOES/'+(config.sector==='conus'?'conus_band.php':config.sector==='fd'?'fulldisk_band.php':'sector_band.php'));
    url.search=new URLSearchParams({sat:config.platform,band:config.product,length:config.length});
    if(!['conus','fd'].includes(config.sector))url.searchParams.set('sector',config.sector);
    return url;
  }
  function timestamp(url){
    const m=new URL(url).pathname.match(/\/(\d{4})(\d{3})(\d{2})(\d{2})_GOES/);
    if(!m)return null;
    const [,year,day,hour,minute]=m.map(Number);
    const date=new Date(Date.UTC(year,0,day,hour,minute));
    if(day<1||day>366||hour>23||minute>59||date.getUTCFullYear()!==year)return null;
    return date;
  }
  function parseFrames(html,config){
    const doc=new DOMParser().parseFromString(html,'text/html');
    const expected=`/GOES${config.platform.slice(1)}/ABI/`;
    const unique=new Map();
    for(const element of doc.querySelectorAll('img[id^="F_"]')){
      try{
        const url=new URL(element.getAttribute('src'));
        const time=timestamp(url);
        // Only use explicitly published NOAA frames for this selection. Never
        // execute scripts or insert markup from the remote document.
        if(url.protocol!=='https:'||url.hostname!=='cdn.star.nesdis.noaa.gov'||!url.pathname.startsWith(expected)||!time)continue;
        const sector=config.sector==='conus'?'CONUS':config.sector==='fd'?'FD':'SECTOR/'+config.sector;
        if(!url.pathname.includes(`/ABI/${sector}/`)||!url.pathname.includes(`-${config.product}-`))continue;
        const link=element.closest('a')?.getAttribute('href');
        let full=url.href;
        if(link){const target=new URL(link);if(target.protocol==='https:'&&target.hostname===url.hostname&&timestamp(target)?.getTime()===time.getTime())full=target.href;}
        unique.set(time.getTime(),{url:url.href,full,time});
      }catch{/* malformed frame is ignored; an empty list fails visibly */}
    }
    return [...unique.values()].sort((a,b)=>a.time-b.time).slice(-Number(config.length));
  }
  function setPlaying(value){
    playing=value;clearTimeout(timer);$('play').textContent=playing?'Pause':'Play';
    if(playing)timer=setTimeout(async()=>{await showFrame((index+1)%frames.length);if(playing)setPlaying(true);},Number($('speed').value));
  }
  function controls(enabled){for(const name of ['first','prev','play','next','latest','slider'])$(name).disabled=!enabled;}
  function resetZoom(){zoom=1;panX=panY=0;applyZoom();}
  function applyZoom(){
    const maxX=stage.clientWidth*(zoom-1)/2,maxY=stage.clientHeight*(zoom-1)/2;
    panX=Math.max(-maxX,Math.min(maxX,panX));panY=Math.max(-maxY,Math.min(maxY,panY));
    image.style.transform=`translate(${panX}px,${panY}px) scale(${zoom})`;
    stage.classList.toggle('zoomed',zoom>1);$('zoom-level').textContent=zoom.toFixed(zoom%1?1:0)+'×';
  }
  function getImage(url){
    if(!cache.has(url)){
      const promise=new Promise((resolve,reject)=>{
        const item=new Image();item.crossOrigin='anonymous';item.decoding='async';
        const timeout=setTimeout(()=>{item.src='';reject(new Error('Satellite image timed out.'));},20000);
        item.onload=()=>{clearTimeout(timeout);resolve(item);};
        item.onerror=()=>{clearTimeout(timeout);reject(new Error('NOAA image could not be loaded. Refresh or try another product.'));};
        item.src=url;
      }).catch(error=>{cache.delete(url);throw error;});
      cache.set(url,promise);
      if(cache.size>26)cache.delete(cache.keys().next().value);
    }
    return cache.get(url);
  }
  function updateStamp(){
    const frame=frames[index];if(!frame)return;
    const age=(Date.now()-frame.time)/60000;
    const time=new Intl.DateTimeFormat('en-US',{timeZone:$('zone').value,month:'short',day:'numeric',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false,timeZoneName:'short'}).format(frame.time);
    $('time').textContent=time;
    $('age').textContent=(age< -10?'CHECK SOURCE CLOCK · ':age>60?'DELAYED IMAGERY · ':'OBSERVED · ')+Math.max(0,Math.round(age))+' min ago';
    stamp.classList.toggle('delayed',age>60||age< -10);
    $('view-label').textContent=$('platform').selectedOptions[0].text+' / '+$('sector').selectedOptions[0].text;
    image.alt=`${$('product').selectedOptions[0].text}, ${$('view-label').textContent}, observed ${frame.time.toISOString()}. NOAA/NESDIS/STAR; GeoColor CIRA/NOAA.`;
  }
  async function showFrame(next){
    if(!frames.length)return false;
    const selection=epoch,serial=++frameSerial;
    const frame=frames[Math.max(0,Math.min(frames.length-1,next))];
    try{
      await getImage(frame.url);
      if(selection!==epoch||serial!==frameSerial)return false;
      image.src=frame.url;
      await image.decode();
      if(selection!==epoch||serial!==frameSerial)return false;
      index=frames.indexOf(frame);image.hidden=false;stamp.hidden=false;$('message').hidden=true;
      $('slider').value=index;$('count').textContent=`${index+1} / ${frames.length}`;
      $('download').href=frame.full;$('download').setAttribute('aria-disabled','false');
      updateStamp();stage.setAttribute('aria-busy','false');
      // Cache only the next two frames, rather than downloading an entire archive.
      for(let offset=1;offset<=2;offset++)getImage(frames[(index+offset)%frames.length].url).catch(()=>{});
      return true;
    }catch(error){
      if(selection!==epoch||serial!==frameSerial)return false;
      setPlaying(false);image.hidden=true;stamp.hidden=true;$('download').removeAttribute('href');$('download').setAttribute('aria-disabled','true');
      $('message').textContent=error.message;$('message').hidden=false;stage.setAttribute('aria-busy','false');return false;
    }
  }
  function syncPlatform(){
    for(const option of $('sector').options)option.disabled=$('platform').value==='G18'&&!['conus','fd'].includes(option.value);
    if($('sector').selectedOptions[0].disabled)$('sector').value='conus';
  }
  async function load(){
    const selection=++epoch;frameSerial++;request?.abort();request=new AbortController();setPlaying(false);controls(false);
    image.hidden=true;stamp.hidden=true;frames=[];cache.clear();resetZoom();
    $('download').removeAttribute('href');$('download').setAttribute('aria-disabled','true');$('count').textContent='— / —';
    $('message').textContent='Loading timestamped NOAA imagery…';$('message').hidden=false;stage.setAttribute('aria-busy','true');
    syncPlatform();const config=configuration(),url=sourceURL(config);$('source').href=url.href;
    const query=new URLSearchParams({...config,zone:$('zone').value});history.replaceState(null,'','?'+query);
    try{
      const response=await fetch(url,{cache:'no-store',signal:AbortSignal.any([request.signal,AbortSignal.timeout(20000)])});
      if(!response.ok)throw new Error(`NOAA imagery list is unavailable (${response.status}).`);
      const html=await response.text();if(selection!==epoch)return;
      if(html.length>2_000_000)throw new Error('Unexpected NOAA imagery response.');
      frames=parseFrames(html,config);if(!frames.length)throw new Error('No timestamped frames are available for this selection. Try another view or use the NOAA viewer link.');
      $('slider').max=frames.length-1;controls(true);
      $('status').textContent=`${$('product').selectedOptions[0].text} · ${frames.length} published frames · NOAA / NESDIS / STAR; GeoColor: CIRA / NOAA. Observations, not a forecast.`;
      await showFrame(frames.length-1);
    }catch(error){
      if(selection!==epoch)return;
      $('message').textContent=error.name==='TimeoutError'?'NOAA took too long to respond. Refresh or open the NOAA viewer.':error instanceof TypeError?'Could not connect to NOAA. Check your connection, try Refresh, or open the NOAA viewer.':error.message;
      $('message').hidden=false;$('status').textContent='Imagery unavailable. The source link opens the selected NOAA product.';stage.setAttribute('aria-busy','false');
    }
  }
  for(const name of choices)$(name).addEventListener('change',load);
  $('refresh').addEventListener('click',load);
  $('zone').addEventListener('change',()=>{updateStamp();const query=new URLSearchParams(location.search);query.set('zone',$('zone').value);history.replaceState(null,'','?'+query);});
  $('play').addEventListener('click',()=>setPlaying(!playing));$('speed').addEventListener('change',()=>{if(playing)setPlaying(true);});
  const go=next=>{setPlaying(false);showFrame(next);};
  $('first').addEventListener('click',()=>go(0));$('latest').addEventListener('click',()=>go(frames.length-1));
  $('prev').addEventListener('click',()=>go((index-1+frames.length)%frames.length));$('next').addEventListener('click',()=>go((index+1)%frames.length));
  $('slider').addEventListener('input',()=>go(Number($('slider').value)));
  $('zoom-in').addEventListener('click',()=>{zoom=Math.min(5,zoom+.5);applyZoom();});$('zoom-out').addEventListener('click',()=>{zoom=Math.max(1,zoom-.5);applyZoom();});$('fit').addEventListener('click',resetZoom);
  stage.addEventListener('pointerdown',event=>{if(zoom<=1||event.target.closest('button'))return;drag={x:event.clientX,y:event.clientY,panX,panY};stage.setPointerCapture(event.pointerId);stage.classList.add('dragging');});
  stage.addEventListener('pointermove',event=>{if(!drag)return;panX=drag.panX+event.clientX-drag.x;panY=drag.panY+event.clientY-drag.y;applyZoom();});
  for(const name of ['pointerup','pointercancel','lostpointercapture'])stage.addEventListener(name,()=>{drag=null;stage.classList.remove('dragging');});
  window.addEventListener('resize',applyZoom);
  $('guide-open').addEventListener('click',()=>{$('guide').showModal();setPlaying(false);});
  $('fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await $('shell').requestFullscreen();}catch{$('status').textContent='Fullscreen is unavailable in this browser.';}});
  if(!$('shell').requestFullscreen)$('fullscreen').hidden=true;
  document.addEventListener('keydown',event=>{
    if(event.target.closest('input,select,button,a,dialog')||$('guide').open||!frames.length)return;
    const actions={ArrowLeft:()=>go((index-1+frames.length)%frames.length),ArrowRight:()=>go((index+1)%frames.length),Home:()=>go(0),End:()=>go(frames.length-1),' ':()=>setPlaying(!playing)};
    if(actions[event.key]){event.preventDefault();actions[event.key]();}
  });
  setInterval(()=>{updateStamp();if($('auto').checked&&!document.hidden&&!playing)load();},300000);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)setPlaying(false);});
  load();
})();
