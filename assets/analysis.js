(() => {
  const $=id=>document.getElementById('analysis-'+id),NS='http://www.w3.org/2000/svg',base=new URL('../generated/analysis/latest.json',document.baseURI);
  let meta,data,zoom=1,panX=0,panY=0,drag,selected,serial=0;
  const stage=document.querySelector('.analysis-stage');
  const node=(tag,attrs={},value)=>{const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(value!==undefined)e.textContent=value;return e;};
  const fahrenheit=value=>value===null?'—':Math.round(value*1.8+32);
  const ftime=value=>new Date(value).toISOString().replace('T',' ').replace('.000','');
  function detail(station){
    selected=station.id;$('station-info').hidden=false;$('station-name').textContent=station.id;
    $('station-time').textContent='Observed '+ftime(station.observation_time);
    $('raw').textContent=station.raw;$('station-values').replaceChildren();
    for(const [label,value] of [['Temperature',fahrenheit(station.temperature_c)+' °F'],['Dewpoint',fahrenheit(station.dewpoint_c)+' °F'],['Wind',station.wind_kt===null?'—':station.wind_kt+' kt'+(station.wind_direction===null?' / VRB':' / '+station.wind_direction+'°')],['Gust',station.gust_kt===null?'—':station.gust_kt+' kt'],['Sea-level pressure',station.slp_hpa===null?'—':station.slp_hpa+' hPa'],['Altimeter',station.altimeter_inhg===null?'—':station.altimeter_inhg+' inHg'],['Visibility',station.visibility_sm===null?'—':station.visibility_sm+' mi'],['Weather',station.weather||'Not reported']]){
      const item=document.createElement('span'),strong=document.createElement('strong');item.textContent=label;strong.textContent=value;item.append(strong);$('station-values').append(item);
    }
  }
  function glyph(station,position){
    const group=node('g',{transform:`translate(${position.x} ${position.y})`,tabindex:'0',role:'button','aria-label':station.id+' observed '+station.observation_time});
    group.append(node('title',{},station.id+' · '+station.observation_time));
    const label=(x,y,value,fill='#ffffff',anchor='start',size=21)=>group.append(node('text',{x,y,fill,'text-anchor':anchor,'font-family':'Arial,sans-serif','font-size':size,'font-weight':'bold',stroke:'#101713','stroke-width':3,'paint-order':'stroke','stroke-linejoin':'round'},value));
    if(selected===station.id)group.append(node('rect',{x:-64,y:-65,width:128,height:115,fill:'#0b6b4555',stroke:'#c19244','stroke-width':2}));
    if(station.temperature_c!==null)label(-13,-12,fahrenheit(station.temperature_c),'#ffb8ad','end');
    if(station.dewpoint_c!==null)label(-13,23,fahrenheit(station.dewpoint_c),'#b4e4bb','end');
    if(station.slp_hpa!==null)label(15,-12,String(Math.round(station.slp_hpa*10)%1000).padStart(3,'0'));
    group.append(node('circle',{r:7,fill:'#f3f5ed',stroke:'#111813','stroke-width':2}));
    if(station.sky_fraction===1)group.append(node('circle',{r:5.8,fill:'#111813'}));
    else if(station.sky_fraction>0){const a=station.sky_fraction*Math.PI*2,x=6*Math.sin(a),y=-6*Math.cos(a);group.append(node('path',{d:`M0 0 L0 -6 A6 6 0 ${station.sky_fraction>.5?1:0} 1 ${x} ${y} Z`,fill:'#111813'}));}
    else if(station.sky_fraction===null)group.append(node('path',{d:'M-4 -4 L4 4 M-4 4 L4 -4',stroke:'#111813','stroke-width':1.5}));
    if(station.wind_kt===0)group.append(node('circle',{r:12,fill:'none',stroke:'#fff','stroke-width':2}));
    else if(station.wind_kt!==null&&position.wind_from_vector){
      const [dx,dy]=position.wind_from_vector,px=-dy,py=dx,length=45;
      const path=node('path',{d:`M${dx*8} ${dy*8} L${dx*length} ${dy*length}`,fill:'none',stroke:'#fff','stroke-width':2.5});group.append(path);
      let speed=Math.floor((station.wind_kt+2.5)/5)*5,at=length;
      while(speed>=50){group.append(node('path',{d:`M${dx*at} ${dy*at} L${dx*(at-10)+px*15} ${dy*(at-10)+py*15} L${dx*(at-10)} ${dy*(at-10)} Z`,fill:'#fff',stroke:'#111813','stroke-width':.7}));speed-=50;at-=13;}
      while(speed>=10){group.append(node('path',{d:`M${dx*at} ${dy*at} l${px*15-dx*6} ${py*15-dy*6}`,stroke:'#fff','stroke-width':2.5}));speed-=10;at-=7;}
      if(speed>=5)group.append(node('path',{d:`M${dx*at} ${dy*at} l${px*8-dx*3} ${py*8-dy*3}`,stroke:'#fff','stroke-width':2.5}));
    }else if(station.wind_kt>0)label(15,19,'VRB','#e8ebe8','start',14);
    label(0,43,station.id,'#e8ebe8','middle',14);
    group.addEventListener('pointerenter',()=>detail(station));group.addEventListener('click',()=>{detail(station);plots();});group.addEventListener('focus',()=>detail(station));group.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();detail(station);}});
    return group;
  }
  function plots(){
    $('stations').replaceChildren();if(!data||!$('overlay').checked)return;
    const region=data.regions.find(r=>r.id===$('region').value),spacing=Number($('density').value)/Math.sqrt(zoom),chosen=[];
    const stations=[...data.stations].sort((a,b)=>(a.id===selected?-1:b.id===selected?1:Date.parse(b.observation_time)-Date.parse(a.observation_time)));
    for(const station of stations){const pos=region.positions[station.id];if(!pos)continue;
      if(station.id!==selected&&chosen.some(p=>Math.hypot(p.x-pos.x,p.y-pos.y)<spacing))continue;
      chosen.push(pos);$('stations').append(glyph(station,pos));
    }
  }
  function transform(){
    const mx=stage.clientWidth*(zoom-1)/2,my=stage.clientHeight*(zoom-1)/2;panX=Math.max(-mx,Math.min(mx,panX));panY=Math.max(-my,Math.min(my,panY));
    $('layer').style.transform=`translate(${panX}px,${panY}px) scale(${zoom})`;stage.classList.toggle('zoomed',zoom>1);plots();
  }
  async function show(){
    if(!meta)return;const token=++serial;
    const item=meta.images.find(p=>p.region===$('region').value&&p.field===$('field').value);
    $('image').hidden=true;$('download').disabled=true;$('stations').replaceChildren();$('message').hidden=false;$('message').textContent='Loading the analysis map…';
    try{
      if(!item||!/^\w+-\w+\.png$/.test(item.image_filename))throw new Error('Unavailable analysis');
      const url=new URL(item.image_filename,base);url.searchParams.set('v',item.image_sha256);$('image').src=url.href;await $('image').decode();if(token!==serial)return;
      $('image').alt=`${meta.analysis_name}: ${$('field').selectedOptions[0].text}, valid ${meta.analysis_valid_utc}. Station observations have separate times.`;
      $('image').hidden=false;$('message').hidden=true;$('download').disabled=false;zoom=1;panX=panY=0;transform();
    }catch{if(token===serial){$('message').textContent='Analysis image unavailable. Use the official NOAA source links in Guide.';}}
  }
  async function load(){
    try{
      const response=await fetch(base,{cache:'no-store',signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error();const manifest=await response.json();
      if(manifest.schema_version!==1||manifest.stations_filename!=='stations.json')throw new Error();
      const url=new URL('stations.json',base);url.searchParams.set('v',manifest.stations_sha256);const stations=await fetch(url,{signal:AbortSignal.timeout(15000)});if(!stations.ok)throw new Error();
      const bytes=await stations.arrayBuffer(),digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');if(digest!==manifest.stations_sha256)throw new Error();
      data=JSON.parse(new TextDecoder().decode(bytes));meta=manifest;
      $('codes').replaceChildren(...data.stations.map(s=>{const e=document.createElement('option');e.value=s.id;return e;}));
      $('times').textContent=`RTMA valid ${ftime(meta.analysis_valid_utc)} · METAR range ${ftime(meta.station_time_min_utc)} to ${ftime(meta.station_time_max_utc)}`;
      const old=Date.now()-Date.parse(meta.analysis_valid_utc)>3*3600000;$('status').dataset.stale=old;
      $('status').textContent=`${old?'OLDER SNAPSHOT · ':''}Generated ${ftime(meta.generated_at_utc)} · ${meta.station_count} stations available · Analysis and observations have different times. Refresh checks the published snapshot.`;
      await show();
    }catch{$('status').textContent='Published analysis unavailable or updating. Try Refresh, or use the official sources in Guide.';$('status').dataset.stale=true;}
  }
  $('region').addEventListener('change',show);$('field').addEventListener('change',show);$('overlay').addEventListener('change',plots);$('density').addEventListener('change',plots);$('refresh').addEventListener('click',load);
  $('in').addEventListener('click',()=>{zoom=Math.min(5,zoom+.5);transform();});$('out').addEventListener('click',()=>{zoom=Math.max(1,zoom-.5);transform();});$('fit').addEventListener('click',()=>{zoom=1;panX=panY=0;transform();});
  stage.addEventListener('pointerdown',e=>{if(zoom<=1||e.target.closest('g,button,aside'))return;drag={x:e.clientX,y:e.clientY,panX,panY};stage.setPointerCapture(e.pointerId);});
  stage.addEventListener('pointermove',e=>{if(drag){panX=drag.panX+e.clientX-drag.x;panY=drag.panY+e.clientY-drag.y;transform();}});
  for(const type of ['pointerup','pointercancel','lostpointercapture'])stage.addEventListener(type,()=>drag=null);
  $('search').addEventListener('submit',async e=>{e.preventDefault();const station=data?.stations.find(s=>s.id===$('query').value.trim().toUpperCase());if(!station){$('status').textContent='No recent observation for that station in this snapshot.';return;}
    if(!data.regions.find(r=>r.id===$('region').value).positions[station.id]){$('region').value='conus';await show();}
    $('overlay').checked=true;detail(station);plots();
  });
  $('station-close').addEventListener('click',()=>{$('station-info').hidden=true;});$('guide-open').addEventListener('click',()=>$('guide').showModal());
  $('download').addEventListener('click',async()=>{
    try{const canvas=document.createElement('canvas');canvas.width=2400;canvas.height=1350;const ctx=canvas.getContext('2d');ctx.drawImage($('image'),0,0,2400,1350);
      if($('overlay').checked){const blob=new Blob([new XMLSerializer().serializeToString($('stations'))],{type:'image/svg+xml'}),url=URL.createObjectURL(blob),image=new Image();try{image.src=url;await image.decode();ctx.drawImage(image,0,0,2400,1350);}finally{URL.revokeObjectURL(url);}}
      ctx.fillStyle='#18191a';ctx.fillRect(0,1285,2400,65);ctx.fillStyle='#9fb4ac';ctx.font='15px Arial';ctx.fillText(`METAR ${ftime(meta.station_time_min_utc)} to ${ftime(meta.station_time_max_utc)} · RTMA ${ftime(meta.analysis_valid_utc)} · NOAA/NCEP/AWC · Natural Earth · CH Weather`,25,1320);
      const link=document.createElement('a');link.href=canvas.toDataURL('image/png');link.download='chweather-rtma-'+$('region').value+'-'+$('field').value+'.png';link.click();
    }catch{$('status').textContent='PNG export failed. Try Refresh and download again.';}
  });
  window.addEventListener('resize',transform);load();
})();
