(() => {
  const $=id=>document.getElementById('enso-'+id),NS='http://www.w3.org/2000/svg',base=new URL('../generated/enso/latest.json',document.baseURI);
  let data,rows=[],oni=new Map(),geometry;
  const signed=(v,digits=2)=>v===null?'—':(v>0?'+':'')+v.toFixed(digits)+'°C';
  const key=r=>r.year+'-'+r.season;
  const node=(tag,attrs={},value)=>{const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(value!==undefined)e.textContent=value;return e;};
  const dateLabel=date=>new Intl.DateTimeFormat('en-US',{timeZone:'UTC',month:'short',day:'numeric',year:'numeric'}).format(new Date(date+'T00:00:00Z'));
  function seasonLabel(r){const format=new Intl.DateTimeFormat('en-US',{timeZone:'UTC',month:'short',year:'numeric'});return r.season+' '+r.year+' / '+format.format(new Date(Date.UTC(r.year,r.center_month-2,1)))+'–'+format.format(new Date(Date.UTC(r.year,r.center_month,1)));}
  function frame(svg,values,height,labels,thresholds=true){
    svg.replaceChildren();const left=65,right=975,top=22,bottom=height-45;
    const good=values.filter(Number.isFinite);const low=Math.floor(Math.min(-1.5,...good)*2)/2-.5,high=Math.ceil(Math.max(1.5,...good)*2)/2+.5;
    const x=i=>left+i*(right-left)/Math.max(1,labels.length-1),y=v=>bottom-(v-low)/(high-low)*(bottom-top);
    if(thresholds)svg.append(node('rect',{x:left,y:top,width:right-left,height:y(.5)-top,fill:'#bf785014'}),node('rect',{x:left,y:y(-.5),width:right-left,height:bottom-y(-.5),fill:'#77a3ae14'}));
    for(let v=Math.ceil(low);v<=high;v++){
      svg.append(node('line',{x1:left,x2:right,y1:y(v),y2:y(v),stroke:'#425748','stroke-width':v===0?1.5:.6}),node('text',{x:left-12,y:y(v)+5,fill:'#9fb4ac','font-size':15,'text-anchor':'end'},v.toFixed(1)));
    }
    if(thresholds)for(const v of [-.5,.5])svg.append(node('line',{x1:left,x2:right,y1:y(v),y2:y(v),stroke:'#9c9d77','stroke-width':1,'stroke-dasharray':'5 5'}));
    for(let tick=0;tick<5;tick++){
      const i=Math.round((labels.length-1)*tick/4);svg.append(node('text',{x:x(i),y:height-12,fill:'#9fb4ac','font-size':16,'text-anchor':tick===0?'start':tick===4?'end':'middle'},labels[i]));
    }
    svg.append(node('text',{x:10,y:19,fill:'#9fb4ac','font-size':15},'°C'));
    return {x,y,top,bottom};
  }
  function line(svg,values,g,color,dashed=false){
    let path='',start=true;values.forEach((value,i)=>{if(value===null||!Number.isFinite(value)){start=true;return;}path+=(start?'M':'L')+g.x(i).toFixed(2)+' '+g.y(value).toFixed(2)+' ';start=false;});
    svg.append(node('path',{d:path,fill:'none',stroke:color,'stroke-width':3,'stroke-linejoin':'round',...(dashed?{'stroke-dasharray':'8 4'}:{})}));
  }
  function sample(){
    if(!geometry||!rows.length)return;const i=Number($('season').value),r=rows[i],comparison=oni.get(key(r));
    $('season-value').textContent=seasonLabel(r)+' · RONI '+signed(r.anomaly_c)+($('compare').checked?' · ONI '+signed(comparison?.anomaly_c??null):'');
    $('history').querySelector('[data-marker]')?.remove();const group=node('g',{'data-marker':''});
    group.append(node('line',{x1:geometry.x(i),x2:geometry.x(i),y1:geometry.top,y2:geometry.bottom,stroke:'#c19244','stroke-width':1}));
    if(r.anomaly_c!==null)group.append(node('circle',{cx:geometry.x(i),cy:geometry.y(r.anomaly_c),r:4,fill:'#e8ebe8',stroke:'#63b38b','stroke-width':2}));
    $('history').append(group);
  }
  function history(preserve=false){
    if(!data)return;const previous=preserve&&rows[Number($('season').value)]?key(rows[Number($('season').value)]):null;
    rows=$('years').value==='all'?data.roni:data.roni.slice(-Number($('years').value)*12);
    const first=rows.map(r=>r.anomaly_c),second=rows.map(r=>oni.get(key(r))?.anomaly_c??null);
    geometry=frame($('history'),first.concat($('compare').checked?second:[]),360,rows.map(r=>r.season+' '+r.year));
    if($('compare').checked)line($('history'),second,geometry,'#c19244',true);line($('history'),first,geometry,'#63b38b');
    const found=previous?rows.findIndex(r=>key(r)===previous):-1;
    $('season').max=rows.length-1;$('season').value=found>=0?found:rows.length-1;$('season').disabled=false;sample();
  }
  function weekly(){
    const values=data.weekly_nino34.slice(-52),chart=$('weekly-chart');
    const g=frame(chart,values.map(v=>v.anomaly_c),300,values.map(v=>v.week_centered.slice(0,7)),false);
    line(chart,values.map(v=>v.anomaly_c),g,'#63b38b');
    const latest=values.at(-1);chart.append(node('circle',{cx:g.x(values.length-1),cy:g.y(latest.anomaly_c),r:4,fill:'#c19244'}));
    $('weekly-latest').textContent='Latest published week: '+dateLabel(latest.week_centered)+' / '+signed(latest.anomaly_c,1);
  }
  function clear(){
    for(const id of ['alert','roni','weekly'])$(id).textContent='—';
    for(const id of ['roni-season','weekly-date','weekly-latest','outlook-date'])$(id).textContent='';
    $('issued').textContent='Official information unavailable.';$('synopsis-box').hidden=true;$('outlook').hidden=true;$('outlook-link').removeAttribute('href');
    $('history').replaceChildren();$('weekly-chart').replaceChildren();$('season').disabled=true;$('season-value').textContent='Index data unavailable.';
  }
  async function load(){
    $('refresh').disabled=true;
    try{
      const response=await fetch(base,{cache:'no-store',signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error();const result=await response.json();
      if(result.schema_version!==1||!Array.isArray(result.roni)||!result.roni.length||!Array.isArray(result.oni)||!result.weekly_nino34?.length||!result.discussion?.alert_status)throw new Error();
      const file=result.official_outlook.image_filename;if(!/^roni-outlook-\d{6}-[a-f0-9]{12}\.png$/.test(file))throw new Error();
      data=result;oni=new Map(data.oni.map(r=>[key(r),r]));
      $('alert').textContent=data.discussion.alert_status;$('issued').textContent='Official discussion: '+dateLabel(data.discussion.issued_date);
      $('roni').textContent=signed(data.latest_roni.anomaly_c);$('roni-season').textContent=seasonLabel(data.latest_roni);
      const latest=data.weekly_nino34.at(-1);$('weekly').textContent=signed(latest.anomaly_c,1);$('weekly-date').textContent='Week centered '+dateLabel(latest.week_centered);
      $('synopsis').textContent=data.discussion.synopsis;$('synopsis-box').hidden=false;$('next').textContent=data.discussion.next_scheduled_date?'Next discussion scheduled by CPC: '+dateLabel(data.discussion.next_scheduled_date)+'.':'';
      $('outlook-date').textContent='Official outlook issued '+data.official_outlook.issued_month+' · Read the season labels and forecast ranges on the graphic.';
      const url=new URL(file,base);url.searchParams.set('v',data.official_outlook.image_sha256);$('outlook').src=url.href;$('outlook').hidden=false;$('outlook-link').href=url.href;
      history();weekly();
      const age=Date.now()-Date.parse(data.generated_at_utc),discussionAge=Date.now()-Date.parse(data.discussion.issued_date+'T00:00:00Z');
      const old=age>48*3600000||discussionAge>50*86400000;
      $('status').dataset.state=old?'stale':'ok';$('status').textContent=(old?'OLDER SNAPSHOT / DISCUSSION · ':'')+'Website snapshot generated '+data.generated_at_utc.replace('T',' ')+'. Source dates differ; the weekly and seasonal indices are not real-time readings.';
    }catch{data=null;clear();$('status').dataset.state='error';$('status').textContent='ENSO data unavailable or updating. Open the official CPC discussion and data links; no neutral status has been assumed.';}
    finally{$('refresh').disabled=false;}
  }
  $('outlook').addEventListener('error',()=>{$('outlook').hidden=true;$('outlook-link').removeAttribute('href');$('outlook-date').textContent='The stored outlook graphic is unavailable. Use the latest official outlook link.';});
  $('years').addEventListener('change',()=>history());$('compare').addEventListener('change',()=>history(true));$('season').addEventListener('input',sample);$('refresh').addEventListener('click',load);
  $('history').addEventListener('pointermove',event=>{if(!rows.length||!geometry||!data)return;const rect=$('history').getBoundingClientRect(),x=(event.clientX-rect.left)/rect.width*1000;const i=Math.max(0,Math.min(rows.length-1,Math.round((x-65)/910*(rows.length-1))));$('season').value=i;sample();});
  $('csv').addEventListener('click',()=>{
    if(!data)return;const merged=new Map();for(const r of data.roni)merged.set(key(r),{...r,roni:r.anomaly_c,oni:null});for(const r of data.oni){if(!merged.has(key(r)))merged.set(key(r),{...r,roni:null});merged.get(key(r)).oni=r.anomaly_c;}
    const records=[...merged.values()].sort((a,b)=>a.year-b.year||a.center_month-b.center_month);
    const csv='center_year,season,center_month,roni_c,oni_c\n'+records.map(r=>[r.year,r.season,r.center_month,r.roni??'',r.oni??''].join(',')).join('\n');
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download='chweather-noaa-enso-indices.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  load();
})();
