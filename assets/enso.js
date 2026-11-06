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
  function graphicBase(svg,title,subtitle,height){
    svg.replaceChildren();svg.append(node('rect',{width:720,height,fill:'#151d18'}));
    svg.append(node('image',{href:new URL('../assets/ch-weather-logo.png',document.baseURI).href,x:20,y:12,width:46,height:46}));
    svg.append(node('text',{x:80,y:32,fill:'#E8EBE8','font-size':19,'font-weight':700},title));
    svg.append(node('text',{x:80,y:53,fill:'#C19244','font-size':11},subtitle));
    svg.append(node('text',{x:20,y:height-14,fill:'#9FB4AC','font-size':10},'CH WEATHER / NOAA CPC observed indices / Snapshot '+data.generated_at_utc.slice(0,10)));
  }
  function houseGraphics(){
    const chart=$('calendar'),latestYear=Math.max(...data.roni.map(r=>r.year)),firstYear=latestYear-29;
    const seasons=['DJF','JFM','FMA','MAM','AMJ','MJJ','JJA','JAS','ASO','SON','OND','NDJ'];
    graphicBase(chart,'THE PACIFIC / 30-YEAR RONI CALENDAR','OVERLAPPING THREE-MONTH SEASONS / OBSERVED INDEX IN CELSIUS',760);
    seasons.forEach((label,i)=>chart.append(node('text',{x:101+i*49,y:90,fill:'#9FB4AC','font-size':11,'text-anchor':'middle'},label)));
    const lookup=new Map(data.roni.map(r=>[key(r),r]));
    for(let y=firstYear;y<=latestYear;y++){
      const py=103+(y-firstYear)*19;
      chart.append(node('text',{x:62,y:py+12,fill:'#9FB4AC','font-size':11,'text-anchor':'end'},y));
      seasons.forEach((season,i)=>{
        const row=lookup.get(y+'-'+season),v=row?.anomaly_c;
        const valid=Number.isFinite(v),color=!valid?'#303b34':Math.abs(v)<.5?'#67786c':v>0?'#D68A54':'#659DAF';
        const label=y+' '+season+': '+(valid?signed(v):'Unavailable');
        const cell=node('rect',{x:78+i*49,y:py,width:46,height:16,fill:color,tabindex:0,role:'img','aria-label':label});
        cell.append(node('title',{},label));
        const read=()=>{$('calendar-readout').textContent=label+' / Three-month observed RONI, not an official episode classification.';};
        cell.addEventListener('pointerenter',read);cell.addEventListener('click',read);cell.addEventListener('focus',read);chart.append(cell);
      });
    }
    [['#659DAF','RONI <= -0.5 C'],['#67786c','Between -0.5 and +0.5 C'],['#D68A54','RONI >= +0.5 C']].forEach(([color,label],i)=>{
      chart.append(node('rect',{x:28+i*228,y:694,width:14,height:12,fill:color}),node('text',{x:48+i*228,y:704,fill:'#E8EBE8','font-size':10},label));
    });
    chart.append(node('text',{x:28,y:727,fill:'#9FB4AC','font-size':10},'Threshold colors describe individual seasons. Adjacent seasons overlap; recent values may be revised.'));
    const common=[...data.roni].reverse().find(r=>Number.isFinite(r.anomaly_c)&&Number.isFinite(oni.get(key(r))?.anomaly_c));
    const compare=$('index-compare');graphicBase(compare,'RONI & ONI / SAME-SEASON COMPARISON',common?seasonLabel(common).toUpperCase():'NO SHARED OBSERVATION AVAILABLE',340);
    if(common){
      const other=oni.get(key(common)),limit=Math.max(1,Math.ceil(Math.max(Math.abs(common.anomaly_c),Math.abs(other.anomaly_c))));
      const x=v=>360+v/limit*260;
      compare.append(node('line',{x1:360,x2:360,y1:85,y2:260,stroke:'#9FB4AC','stroke-dasharray':'4 4'}));
      for(const [i,name,v,color] of [[0,'RONI',common.anomaly_c,'#63B38B'],[1,'ONI',other.anomaly_c,'#C19244']]){
        const py=120+i*80;
        compare.append(node('rect',{x:Math.min(360,x(v)),y:py,width:Math.max(1,Math.abs(x(v)-360)),height:30,fill:color}),node('text',{x:32,y:py+21,fill:'#E8EBE8','font-size':17},name),node('text',{x:650,y:py+21,fill:'#E8EBE8','font-size':18,'text-anchor':'end'},signed(v)));
      }
      for(const v of [-limit,0,limit])compare.append(node('text',{x:x(v),y:285,fill:'#9FB4AC','font-size':12,'text-anchor':'middle'},v+' C'));
      $('index-note').textContent=seasonLabel(common)+'. RONI '+signed(common.anomaly_c)+'; ONI '+signed(other.anomaly_c)+'. These are distinct indices, not competing forecasts.';
    }
  }
  document.querySelectorAll('[data-enso-save]').forEach(button=>button.addEventListener('click',()=>{
    if(!data)return;const svg=$(''+button.dataset.ensoSave).cloneNode(true);svg.setAttribute('xmlns',NS);
    // Keep exports self-contained: a text wordmark replaces the external logo image.
    svg.querySelectorAll('image').forEach(image=>image.remove());
    const blob=new Blob([new XMLSerializer().serializeToString(svg)],{type:'image/svg+xml;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download='CHWeather_ENSO_'+button.dataset.ensoSave+'_'+data.generated_at_utc.slice(0,10)+'.svg';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }));
  function forecastGraphic(){
    const svg=$('forecast'),rows=data.forecast_quantiles;
    svg.replaceChildren();
    if(!Array.isArray(rows)||rows.length<6){$('forecast-status').textContent='Forecast numbers are not in this published snapshot yet. Run Daily weather and sunset outlooks to refresh ENSO; the official source remains linked above.';return;}
    if(rows.some(r=>!Array.isArray(r.quantiles_c)||r.quantiles_c.length!==7||r.quantiles_c.some((v,i,a)=>!Number.isFinite(v)||v < -6||v>6||(i&&v<a[i-1]))))throw new Error('Invalid forecast quantiles');
    const values=rows.flatMap(r=>r.quantiles_c),low=Math.floor(Math.min(-.5,...values)*2)/2-.25,high=Math.ceil(Math.max(.5,...values)*2)/2+.25;
    const x=i=>80+i*850/(rows.length-1),y=v=>360-(v-low)/(high-low)*255;
    svg.append(node('rect',{width:1000,height:480,fill:'#151d18'}),node('image',{href:new URL('../assets/ch-weather-logo.png',document.baseURI).href,x:20,y:12,width:60,height:60}),node('text',{x:95,y:37,fill:'#E8EBE8','font-size':25,'font-weight':700},'CH WEATHER / ENSO OUTLOOK'),node('text',{x:95,y:62,fill:'#C19244','font-size':14},'CPC NUMERICAL GUIDANCE / ISSUED '+data.official_outlook.issued_month.toUpperCase()));
    for(let v=Math.ceil(low*2)/2;v<=high;v+=.5)svg.append(node('line',{x1:80,x2:930,y1:y(v),y2:y(v),stroke:'#567160','stroke-width':1,'stroke-opacity':.5}),node('text',{x:65,y:y(v)+4,fill:'#9FB4AC','font-size':13,'text-anchor':'end'},v.toFixed(1)));
    [[0,6,.18],[1,5,.28],[2,4,.5]].forEach(([a,b,opacity])=>{
      const path=rows.map((r,i)=>(i?'L':'M')+x(i)+' '+y(r.quantiles_c[a])).join(' ')+rows.map((r,i)=>[r,i]).reverse().map(([r,i])=>'L'+x(i)+' '+y(r.quantiles_c[b])).join(' ')+' Z';
      svg.append(node('path',{d:path,fill:'#55AC7F',opacity}));
    });
    svg.append(node('path',{d:rows.map((r,i)=>(i?'L':'M')+x(i)+' '+y(r.quantiles_c[3])).join(' '),stroke:'#E3B669','stroke-width':3,fill:'none'}));
    rows.forEach((r,i)=>{svg.append(node('text',{x:x(i),y:385,fill:'#E8EBE8','font-size':14,'text-anchor':'middle'},r.season));const dot=node('circle',{cx:x(i),cy:y(r.quantiles_c[3]),r:5,fill:'#E3B669'});dot.append(node('title',{},r.season+' median '+r.quantiles_c[3]+' C; 5th–95th '+r.quantiles_c[0]+' to '+r.quantiles_c[6]+' C'));svg.append(dot);});
    svg.append(node('text',{x:80,y:92,fill:'#9FB4AC','font-size':12},'RONI / °C'),node('text',{x:80,y:420,fill:'#E3B669','font-size':14},'Median'),node('text',{x:200,y:420,fill:'#9FB4AC','font-size':14},'Green bands: middle 50% / 70% / 90% forecast ranges'),node('text',{x:24,y:458,fill:'#9FB4AC','font-size':12},'Source: NOAA CPC / CH Weather visualization / Overlapping three-month seasons'));
    $('forecast-status').textContent='Official CPC forecast values, drawn in CH Weather’s graphic system. Hover over a gold point for exact quantiles.';
  }
  function clear(){
    for(const id of ['alert','roni','weekly'])$(id).textContent='—';
    for(const id of ['roni-season','weekly-date','weekly-latest','outlook-date'])$(id).textContent='';
    $('issued').textContent='Official information unavailable.';$('synopsis-box').hidden=true;$('outlook').hidden=true;$('outlook-link').removeAttribute('href');
    $('forecast').replaceChildren();$('calendar').replaceChildren();$('index-compare').replaceChildren();$('index-note').textContent='Observed comparison unavailable.';$('history').replaceChildren();$('weekly-chart').replaceChildren();$('season').disabled=true;$('season-value').textContent='Index data unavailable.';
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
      $('outlook').hidden=true;
      forecastGraphic();
      history();weekly();houseGraphics();
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
