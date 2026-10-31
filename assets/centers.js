(() => {
  const $=id=>document.getElementById('centers-'+id);
  const manifestURL=new URL('../generated/centers/latest.json',document.baseURI);
  let manifest,center='wpc',serial=0,productID=new URLSearchParams(location.search).get('product');
  const requestedCenter=new URLSearchParams(location.search).get('center');if(requestedCenter==='cpc')center='cpc';
  function status(message,state='ok'){$('status').textContent=message;$('status').dataset.state=state;}
  function safeURL(value){const url=new URL(value);if(url.protocol!=='https:'||!['www.wpc.ncep.noaa.gov','www.cpc.ncep.noaa.gov'].includes(url.hostname))throw new Error('Unexpected outlook source.');return url.href;}
  function populate(){
    for(const button of document.querySelectorAll('[data-center]'))button.setAttribute('aria-pressed',String(button.dataset.center===center));
    const available=manifest.products.filter(p=>p.center===center);
    const selected=available.find(p=>p.id===productID);
    const groups=[...new Set(available.map(p=>p.group))],old=$('field').value;
    $('field').replaceChildren(...groups.map(group=>{const option=document.createElement('option');option.value=group;option.textContent=({ero:'Excessive rainfall',qpf:'Precipitation totals',temperature:'Temperature',precipitation:'Precipitation'})[group];return option;}));
    $('field').value=selected?.group||(groups.includes(old)?old:groups[0]);$('field').disabled=false;
    periods(selected?.id);
  }
  function periods(preferred){
    const previousPeriod=manifest.products.find(p=>p.id===$('period').value)?.period;
    const values=manifest.products.filter(p=>p.center===center&&p.group===$('field').value);
    $('period').replaceChildren(...values.map(p=>{const option=document.createElement('option');option.value=p.id;option.textContent=p.period;return option;}));
    if(values.some(p=>p.id===preferred))$('period').value=preferred;
    else if(values.some(p=>p.period===previousPeriod))$('period').value=values.find(p=>p.period===previousPeriod).id;
    $('period').disabled=false;show();
  }
  async function loadImage(url,selection){
    const image=new Image();image.decoding='async';
    await new Promise((resolve,reject)=>{const timer=setTimeout(()=>{image.src='';reject(new Error('Image request timed out.'));},20000);image.onload=()=>{clearTimeout(timer);resolve();};image.onerror=()=>{clearTimeout(timer);reject(new Error('The official server could not load this graphic in your browser.'));};image.src=url;});
    if(selection!==serial)return false;
    $('image').src=url;await $('image').decode();if(selection!==serial)return false;
    $('image').hidden=false;$('image-link').href=url;return true;
  }
  async function show(){
    const item=manifest.products.find(p=>p.id===$('period').value);if(!item)return;
    const selection=++serial;productID=item.id;history.replaceState(null,'','?'+new URLSearchParams({center,product:productID}));
    $('image').hidden=true;$('image-link').removeAttribute('href');$('title').textContent=item.title;
    $('source-name').textContent='NOAA / NWS / '+center.toUpperCase()+' · OFFICIAL GRAPHIC';$('description').textContent=item.description;
    $('official').href=safeURL(item.official_page_url);$('image').alt=`Official ${center.toUpperCase()} ${item.title}. Read issuance, validity and the legend printed on this map.`;
    $('retrieved').textContent='';status('Loading the selected official graphic…');
    const snapshot=new URL(item.image_filename,manifestURL);snapshot.searchParams.set('v',item.image_sha256);
    try{
      if($('mode').value==='official'){
        const url=new URL(safeURL(item.source_url));url.searchParams.set('chwx_refresh',Math.floor(Date.now()/300000));
        try{
          if(!await loadImage(url.href,selection))return;
          status('Loaded directly from the official server. Read the issuance and valid period on the map; a successful image request does not guarantee a new issuance.');
          $('retrieved').textContent='DIRECT SOURCE REQUEST · '+new Date().toISOString().replace('T',' ');return;
        }catch(error){if(selection!==serial)return;$('mode').value='snapshot';status('The official server blocked or could not load the direct image. Showing the dated published snapshot below.','stale');}
      }
      const fallback=$('status').dataset.state==='stale';
      if(!await loadImage(snapshot.href,selection))return;
      const old=Date.now()-Date.parse(item.retrieved_at_utc)>30*3600000;
      if(!fallback)status(old?'This published snapshot is more than 30 hours old. Check the official source for newer guidance.':'Published snapshot. Check the issuance and exact valid interval on the map; newer guidance may be available at the official source.',old?'stale':'ok');
      $('retrieved').textContent='SNAPSHOT RETRIEVED · '+item.retrieved_at_utc.replace('T',' ');
    }catch(error){if(selection===serial){$('image').hidden=true;$('image-link').removeAttribute('href');status('This graphic is unavailable. Open “Official source & discussion” for the latest outlook.','error');}}
  }
  async function load(){
    serial++;$('image').hidden=true;status('Loading published WPC/CPC outlooks…');
    try{
      const response=await fetch(manifestURL,{cache:'no-store',signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error('Missing outlook catalog');
      const data=await response.json();
      if(data.schema_version!==1||!Array.isArray(data.products)||!data.products.length)throw new Error('Invalid outlook catalog');
      for(const p of data.products){if(!/^(?:wpc|cpc)-[a-z0-9-]+\.png$/.test(p.image_filename)||!['wpc','cpc'].includes(p.center)||!Number.isFinite(Date.parse(p.retrieved_at_utc)))throw new Error('Invalid outlook item');safeURL(p.source_url);safeURL(p.official_page_url);}
      manifest=data;
      const selected=manifest.products.find(p=>p.id===productID);if(selected)center=selected.center;
      populate();
    }catch{status('Published outlooks are unavailable. Use the WPC and CPC source links below.','error');}
  }
  for(const button of document.querySelectorAll('[data-center]'))button.addEventListener('click',()=>{center=button.dataset.center;productID=null;if(manifest)populate();});
  $('field').addEventListener('change',()=>periods());$('period').addEventListener('change',show);$('mode').addEventListener('change',()=>{if(manifest)show();});$('refresh').addEventListener('click',load);
  setInterval(()=>{if(!document.hidden&&manifest&&$('mode').value==='official')show();},300000);
  load();
})();
