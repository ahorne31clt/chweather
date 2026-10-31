(() => {
  const $=id=>document.getElementById('mos-'+id);
  const families={MAV:{label:'GFS / MAV',header:'GFS MOS',stale:18,note:'Short-range GFS MOS. Use the HR clock-hour row with DT dates; all bulletin times are UTC.'},MET:{label:'NAM / MET',header:'NAM MOS',stale:18,note:'NAM MOS. Use the HR clock-hour row with DT dates; all bulletin times are UTC.'},MEX:{label:'Extended GFS / MEX',header:'GFSX MOS',stale:30,note:'Extended GFS MOS. FHR gives hours after initialization, not UTC clock hours. WND is maximum sustained wind during its specified interval; QPF and other coded rows require the MEX reference.'},LAV:{label:'GFS LAMP / LAV',header:'GFS LAMP',stale:3,note:'Short-range LAMP guidance. Use the UTC clock-hour row and the bulletin header date. LAMP and MOS products can have different update times and forecast intervals.'}};
  let current,sequence=0,controller,catalogPromise,selected='KCLT';
  function status(value,state='ok'){$('status').textContent=value;$('status').dataset.state=state;}
  function catalog(){
    if(!catalogPromise)catalogPromise=fetch('../generated/models/airports/catalog.json',{signal:AbortSignal.timeout(10000)}).then(r=>r.ok?r.json():[]).then(d=>Array.isArray(d)?d.filter(a=>/^K[A-Z0-9]{3}$/.test(a.icao)):[]).catch(()=>[]);
    return catalogPromise;
  }
  function parseBulletin(raw,station,product){
    if(raw.length>100000||/<html|<!doctype/i.test(raw))throw new Error('The provider did not return a valid MOS bulletin.');
    const clean=raw.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g,'').replace(/\r\n?/g,'\n').trim();
    const headers=[...clean.matchAll(/^([A-Z0-9]{3,4})\s+(GFSX? MOS|NAM MOS|GFS LAMP)\s+GUIDANCE\s+(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{2})(\d{2})\s+UTC/gm)];
    const header=headers.find(h=>(h[1]===station||h[1]===station.slice(1))&&h[2]===families[product].header);
    if(headers.length!==1||!header)throw new Error(`No matching ${product} bulletin is available for ${station}. The airport may not have this guidance family.`);
    const month=Number(header[3]),day=Number(header[4]),year=Number(header[5]),hour=Number(header[6]),minute=Number(header[7]);
    const runtime=new Date(Date.UTC(year,month-1,day,hour,minute));
    if(runtime.getUTCFullYear()!==year||runtime.getUTCMonth()!==month-1||runtime.getUTCDate()!==day||hour>23||minute>59||runtime-Date.now()>600000)throw new Error('The bulletin has an invalid or future initialization time.');
    const row=clean.match(/^(HR|UTC|FHR)\s+(.+)$/m);
    if(!row||!/^TMP\s+.+$/m.test(clean))throw new Error('The bulletin is incomplete; no substituted guidance was used.');
    return {clean,runtime,row:row[1],raw};
  }
  async function load(station,airport){
    const token=++sequence;controller?.abort();controller=new AbortController();current=null;
    $('content').hidden=true;$('matches').replaceChildren();$('action-status').textContent='';selected=station;$('query').value=station;
    const product=$('product').value;
    if(!/^K[A-Z0-9]{3}$/.test(station)||!families[product]){status('Enter a CONUS K-prefixed ICAO code such as KCLT, or its three-character FAA code such as CLT.','error');return;}
    const url=new URL('https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py');url.search=new URLSearchParams({pil:product+station.slice(1),limit:1});
    status(`Retrieving the latest available ${product} bulletin for ${station}…`);
    try{
      const response=await fetch(url,{cache:'no-store',signal:AbortSignal.any([controller.signal,AbortSignal.timeout(20000)])});
      if(!response.ok)throw new Error(`The MOS provider returned ${response.status}. Please try again later.`);
      const raw=await response.text();if(token!==sequence)return;
      const parsed=parseBulletin(raw,station,product);
      const retrieved=new Date(),age=(Date.now()-parsed.runtime)/3600000,old=age>families[product].stale;
      current={...parsed,station,product,url:url.href};
      $('title').textContent=station+' / '+families[product].label;
      $('airport-name').textContent=airport?[airport.name,airport.city,airport.state].filter(Boolean).join(' · '):'CONUS station lookup · availability varies by airport and guidance family';
      $('runtime').textContent=parsed.runtime.toISOString().replace('T',' ').replace('.000','');
      $('retrieved').textContent=retrieved.toISOString().replace('T',' ').replace('.000','');
      $('time-row').textContent=parsed.row==='FHR'?'FHR · hours after initialization':parsed.row+' · UTC clock hours; follow bulletin dates';
      $('family-note').textContent=families[product].note;
      if(!airport)catalog().then(airports=>{if(token!==sequence)return;const found=airports.find(a=>a.icao===station);if(found)$('airport-name').textContent=[found.name,found.city,found.state].filter(Boolean).join(' · ');});
      $('bulletin').textContent=parsed.clean;$('source').href=url.href;$('content').hidden=false;
      history.replaceState(null,'','?'+new URLSearchParams({station,product}));
      status(`${old?'OLDER GUIDANCE · ':''}Latest available ${product} for ${station}, initialized ${parsed.runtime.toISOString().replace('T',' ').replace('.000','')}. Retrieved from IEM; this is model guidance, not a current observation or an official point forecast.`,old?'stale':'ok');
    }catch(error){if(token!==sequence)return;current=null;$('content').hidden=true;status(error.name==='TimeoutError'?'The MOS provider took too long to respond. Please try again.':error instanceof TypeError?'Could not connect to the MOS provider. Check your connection or try again later.':error.message,'error');}
  }
  $('search').addEventListener('submit',async event=>{
    event.preventDefault();const query=$('query').value.trim(),upper=query.toUpperCase();
    if(/^K[A-Z0-9]{3}$/.test(upper)){load(upper);return;}
    const token=++sequence;controller?.abort();current=null;$('content').hidden=true;$('matches').replaceChildren();status('Finding matching CONUS airports…');
    const airports=await catalog();if(token!==sequence)return;
    const exact=airports.find(a=>a.icao===upper||a.iata===upper||a.local===upper);
    if(exact){load(exact.icao,exact);return;}
    if(/^[A-Z0-9]{3}$/.test(upper)){load('K'+upper);return;}
    const rank=a=>((a.city||'').toLowerCase().startsWith(query.toLowerCase())?10:0)+(a.type==='large_airport'?3:a.type==='medium_airport'?2:0);
    const matches=airports.filter(a=>[a.icao,a.iata,a.name,a.city].join(' ').toLowerCase().includes(query.toLowerCase())).sort((a,b)=>rank(b)-rank(a)).slice(0,10);
    if(query.length<2||!matches.length){status('No matching airport found. Enter its ICAO code directly, such as KCLT. Not every airport has MOS guidance.','error');return;}
    status('Choose an airport:');
    for(const airport of matches){const button=document.createElement('button');button.type='button';button.textContent=`${airport.icao} · ${airport.name} · ${airport.city||airport.state}`;button.addEventListener('click',()=>load(airport.icao,airport));$('matches').append(button);}
  });
  $('product').addEventListener('change',()=>load(selected));$('refresh').addEventListener('click',()=>load(selected));
  for(const button of document.querySelectorAll('[data-station]'))button.addEventListener('click',()=>load(button.dataset.station));
  $('download').addEventListener('click',()=>{if(!current)return;const url=URL.createObjectURL(new Blob([current.raw],{type:'text/plain;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download=`${current.station}-${current.product}-${current.runtime.toISOString().replace(/[-:]/g,'').slice(0,13)}.txt`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  $('copy').addEventListener('click',async()=>{if(!current)return;try{await navigator.clipboard.writeText(current.clean);$('action-status').textContent='Bulletin text copied.';}catch{const range=document.createRange();range.selectNodeContents($('bulletin'));const selection=getSelection();selection.removeAllRanges();selection.addRange(range);$('action-status').textContent='Bulletin text selected. Use your browser’s Copy command.';}});
  $('share').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(location.href);$('action-status').textContent='Link to this station and guidance family copied.';}catch{$('action-status').textContent='Copy the address bar to share this station and guidance family.';}});
  const params=new URLSearchParams(location.search);if(families[params.get('product')])$('product').value=params.get('product');
  const station=params.get('station');load(/^K[A-Z0-9]{3}$/.test(station)?station:'KCLT');
  catalog();
})();
