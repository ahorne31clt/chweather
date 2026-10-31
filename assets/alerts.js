/* Official NWS active bulletins; never fabricate a zero on a failed request. */
(() => {
  const board=document.getElementById('alerts-list'),mini=document.querySelector('[data-alert-summary]');
  if(!board&&!mini)return;
  const $=id=>document.getElementById('alerts-'+id);
  const STATES={AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',DC:'District of Columbia',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',PR:'Puerto Rico',VI:'US Virgin Islands',GU:'Guam',MP:'Northern Mariana Islands',AS:'American Samoa'};
  let raw=[],checked=0,sourceUpdated=0,failed=false,loading=false,pageSize=30,request;
  const time=n=>{const value=Date.parse(n);return Number.isFinite(value)?value:null;};
  const text=(tag,value,cls)=>{const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;return e;};
  const kind=p=>/warning/i.test(p.event)?'warning':/watch/i.test(p.event)?'watch':/advisory/i.test(p.event)?'advisory':'other';
  const matches=(p,value)=>value==='all'||value==='tornado'&&p.event==='Tornado Warning'||value==='severe'&&p.event==='Severe Thunderstorm Warning'||value==='flash'&&p.event==='Flash Flood Warning'||value===kind(p);
  const states=p=>new Set((p.geocode?.UGC||[]).map(code=>code.slice(0,2)).filter(code=>STATES[code]));
  const MARINE_PREFIXES=new Set(['AM','AN','GM','LC','LE','LH','LM','LO','LS','PH','PK','PM','PS','PZ','SL']);
  // NWS marine zones are also served below /zones/forecast/, so use their
  // official UGC prefixes rather than assuming a /marine/ URL path.
  const marine=p=>(p.geocode?.UGC||[]).some(code=>MARINE_PREFIXES.has(code.slice(0,2)))||(p.affectedZones||[]).some(url=>/\/zones\/marine\//.test(url));
  function activeMessages(features,now=Date.now()){
    const replaced=new Set(),ids=new Map();
    // Process references on actual cancellations/updates even though cancellation
    // messages themselves are never displayed as active warnings.
    for(const f of features){const p=f?.properties;if(!p||p.status!=='Actual')continue;
      if(['Update','Cancel'].includes(p.messageType))for(const ref of p.references||[])if(ref.identifier)replaced.add(ref.identifier);
    }
    for(const f of features){const p=f?.properties;if(!p||p.status!=='Actual'||!['Alert','Update'].includes(p.messageType)||typeof p.event!=='string')continue;
      const expiry=time(p.expires),end=time(p.ends),sent=time(p.sent),id=p.id||f.id;
      if(!id||!sent||!expiry||expiry<=now||(end!==null&&end<=now)||replaced.has(p.id)||replaced.has(f.id))continue;
      const previous=ids.get(id);
      if(!previous||sent>time(previous.sent))ids.set(id,{...p,_url:f.id||p['@id']});
    }
    return [...ids.values()];
  }
  function fresh(){return checked&&Date.now()-checked<=300000&&!failed&&(!sourceUpdated||Date.now()-sourceUpdated<=1800000);}
  function health(message,state){
    if(board){$('health').textContent=message;document.querySelector('.alerts-health').dataset.health=state;}
    if(mini){mini.dataset.health=state;mini.querySelector('.alerts-mini-status').textContent=message;}
  }
  function format(value){const date=time(value);return date===null?'Not specified':new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(new Date(date));}
  function priority(p){
    const events={'Tornado Warning':1000,'Tsunami Warning':1000,'Flash Flood Warning':980,'Severe Thunderstorm Warning':960,'Hurricane Warning':940,'Storm Surge Warning':940};
    return events[p.event]||({warning:700,watch:500,advisory:300,other:100}[kind(p)]+({Extreme:40,Severe:30,Moderate:20,Minor:10}[p.severity]||0));
  }
  function officialLink(p){
    try{const url=new URL(p._url);if(url.protocol==='https:'&&url.hostname==='api.weather.gov'&&url.pathname.startsWith('/alerts/'))return url.href;}catch{}
    return 'https://www.weather.gov/';
  }
  function card(p){
    const article=document.createElement('article');article.className='alert-card';article.dataset.kind=kind(p);
    const header=text('div','','alert-card-header'),title=text('div','');
    title.append(text('p',`${kind(p).toUpperCase()} / ${p.senderName||'NATIONAL WEATHER SERVICE'}`,'eyebrow'),text('h3',p.event));
    const expiry=time(p.expires),hazardEnd=time(p.ends),end=Math.min(expiry??Infinity,hazardEnd??Infinity),minutes=Math.max(1,Math.ceil((end-Date.now())/60000));
    const ending=hazardEnd!==null&&hazardEnd<expiry?'Hazard ends':'Message expires';
    header.append(title,text('span',minutes<60?`${ending} in ${minutes} min`:`${ending} ${format(new Date(end).toISOString())}`,'alert-expiry'));
    article.append(header,text('p',p.areaDesc||'Read the official message for affected areas.','alert-area'));
    if(p.headline)article.append(text('p',p.headline,'alert-headline'));
    const times=text('div','','alert-timing');
    times.append(text('span','Issued '+format(p.sent)),text('span','Expires '+format(p.expires)));
    if(p.onset)times.append(text('span','Hazard onset '+format(p.onset)));
    if(p.ends)times.append(text('span','Hazard ends '+format(p.ends)));
    article.append(times);
    const details=document.createElement('details');details.append(text('summary','Read official details & protective actions'));
    if(p.instruction){details.append(text('p','NWS INSTRUCTIONS','eyebrow'),text('p',p.instruction,'alert-full'));}
    details.append(text('p',p.description||'Read the official bulletin for details.','alert-full'));
    const link=text('a','Official NWS alert data ↗','text-link');link.href=officialLink(p);link.target='_blank';link.rel='noopener';details.append(link);article.append(details);
    return article;
  }
  function render(){
    const messages=activeMessages(raw),isFresh=fresh();
    if(mini){
      for(const [selector,value] of [['[data-alert-national]',messages.filter(p=>kind(p)==='warning').length],['[data-alert-nc]',messages.filter(p=>kind(p)==='warning'&&states(p).has('NC')).length],['[data-alert-tornado]',messages.filter(p=>p.event==='Tornado Warning').length]])mini.querySelector(selector).textContent=isFresh?value:'—';
    }
    if(!board)return;
    const area=$('area').value,scope=messages.filter(p=>area==='all'||area==='marine'&&marine(p)||states(p).has(area));
    for(const button of document.querySelectorAll('[data-counter]')){
      button.querySelector('strong').textContent=isFresh?scope.filter(p=>matches(p,button.dataset.counter)).length:'—';
      button.setAttribute('aria-pressed',String($('kind').value===button.dataset.counter));
    }
    $('count-note').textContent=`Counters cover ${area==='all'?'all NWS land and marine coverage':area==='marine'?'NWS marine zones':STATES[area]}. They count distinct active bulletins, not storms, counties, or people. Type and text filters affect the list below, not these counters.`;
    const query=$('query').value.trim().toLowerCase();
    const filtered=scope.filter(p=>matches(p,$('kind').value)&&(!query||[p.event,p.areaDesc,p.headline,p.senderName].join(' ').toLowerCase().includes(query)));
    filtered.sort((a,b)=>$('sort').value==='newest'?time(b.sent)-time(a.sent):$('sort').value==='expires'?time(a.expires)-time(b.expires):priority(b)-priority(a)||time(b.sent)-time(a.sent));
    const open=new Set([...board.querySelectorAll('details[open]')].map(e=>e.parentElement.dataset.id));
    const focused=document.activeElement;
    const focusedCard=focused?.closest('.alert-card');
    const focusID=board.contains(focused)?focusedCard?.dataset.id:null;
    const focusIndex=focusedCard?[...focusedCard.querySelectorAll('summary,a')].indexOf(focused):-1;
    const fragment=document.createDocumentFragment();
    for(const p of filtered.slice(0,pageSize)){const element=card(p);element.dataset.id=p.id;if(open.has(p.id))element.querySelector('details').open=true;fragment.append(element);}
    if(!filtered.length){const empty=text('div','','alert-empty');empty.append(text('h3',!checked?'Alert data unavailable.':!isFresh?'No matching bulletins in the last snapshot.':query||$('kind').value!=='all'?'No matching active bulletins.':'No active bulletins in this selection.'));empty.append(text('p',!checked?'Try Refresh or check weather.gov for official alerts.':!isFresh?'The feed could not be verified as current. Check weather.gov for the latest alerts.':'This describes the selected feed and filters; it is not a guarantee of hazard-free weather.'));fragment.append(empty);}
    board.replaceChildren(fragment);$('more').hidden=filtered.length<=pageSize;
    if(focusID&&focusIndex>=0){
      const replacement=[...board.children].find(e=>e.dataset.id===focusID);
      replacement?.querySelectorAll('summary,a')[focusIndex]?.focus({preventScroll:true});
    }
    $('total').textContent=checked?`${scope.length} ${isFresh?'active':'last-snapshot'} bulletins in this coverage`:'';
    $('results-note').textContent=checked?`${isFresh?'Showing':'Last snapshot:'} ${Math.min(pageSize,filtered.length)} of ${filtered.length} matching bulletins. Times use your browser’s local time zone.`:'Waiting for a successful NWS response. Counters remain unavailable.';
  }
  async function fetchAlerts(){
    if(loading)return;loading=true;request=new AbortController();if(board)$('refresh').disabled=true;
    if(!checked)health('Connecting to the National Weather Service…','loading');
    try{
      let url=new URL('https://api.weather.gov/alerts/active'),features=[],updated=null;
      const seen=new Set();
      for(let page=0;url;page++){
        if(page>=8||seen.has(url.href)||url.protocol!=='https:'||url.hostname!=='api.weather.gov'||!url.pathname.startsWith('/alerts'))throw new Error('NWS returned an incomplete or unexpected alert list.');
        seen.add(url.href);
        const response=await fetch(url,{headers:{Accept:'application/geo+json'},cache:'no-store',signal:AbortSignal.any([request.signal,AbortSignal.timeout(20000)])});
        if(!response.ok)throw new Error(`NWS returned ${response.status}.`);
        const data=await response.json();
        if(data.type!=='FeatureCollection'||!Array.isArray(data.features))throw new Error('Unexpected NWS alert response.');
        features.push(...data.features);if(features.length>5000)throw new Error('NWS alert list exceeded the supported size.');
        const modified=time(data.updated);if(modified!==null)updated=updated===null?modified:Math.min(updated,modified);
        url=data.pagination?.next?new URL(data.pagination.next):null;
      }
      raw=features;checked=Date.now();sourceUpdated=updated;failed=false;
      if(!fresh())health(`DELAYED FEED · Source last updated ${format(new Date(sourceUpdated).toISOString())}. Counters unavailable; check weather.gov.`,'stale');
      else health(`Checked ${format(new Date(checked).toISOString())} · NWS${sourceUpdated?' feed updated '+format(new Date(sourceUpdated).toISOString()):''} · Checks every ${board?'minute':'2 minutes'}.`,'ok');
      render();
    }catch(error){
      failed=true;
      health(`NWS connection unavailable. ${checked?'Last successful check '+format(new Date(checked).toISOString())+'. Showing the remaining last-snapshot messages.':'No current counts available.'} Check weather.gov or try Refresh.` ,checked?'stale':'error');
      render();
    }finally{loading=false;if(board)$('refresh').disabled=false;}
  }
  if(board){
    const existing=new Set([...$('area').options].map(o=>o.value));
    for(const [code,name] of Object.entries(STATES).sort((a,b)=>a[1].localeCompare(b[1])))if(!existing.has(code)){const option=text('option',name);option.value=code;$('area').append(option);}
    const params=new URLSearchParams(location.search);
    for(const key of ['area','kind'])if([...$(key).options].some(o=>o.value===params.get(key)))$(key).value=params.get(key);
    function filters(){pageSize=30;const query=new URLSearchParams({area:$('area').value,kind:$('kind').value});history.replaceState(null,'','?'+query);render();}
    for(const key of ['area','kind','sort'])$(key).addEventListener('change',filters);
    $('query').addEventListener('input',()=>{pageSize=30;render();});
    for(const button of document.querySelectorAll('[data-counter]'))button.addEventListener('click',()=>{$('kind').value=button.dataset.counter;filters();$('list-title').scrollIntoView({behavior:'smooth',block:'start'});});
    $('refresh').addEventListener('click',fetchAlerts);$('more').addEventListener('click',()=>{pageSize+=30;render();});
  }
  setInterval(()=>{if(!document.hidden)fetchAlerts();},board?60000:120000);
  setInterval(()=>{if(!document.hidden){if(checked&&!fresh()&&!failed)health('Feed is stale. Counters unavailable until the next successful current check.','stale');render();}},30000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-checked>60000)fetchAlerts();});
  fetchAlerts();
})();
