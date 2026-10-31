(() => {
  const image=document.querySelector('#tropical-image');if(!image)return;
  const status=document.querySelector('#tropical-status'),days=document.querySelector('#tropical-days'),mode=document.querySelector('#tropical-mode');
  const snapshot=document.querySelector('#tropical-snapshot'),base=new URL('../generated/tropical/latest.json',document.baseURI);
  let manifest,basin='atl',request=0;
  const date=value=>new Intl.DateTimeFormat('en-US',{timeZone:'UTC',month:'short',day:'numeric',year:'numeric',hour:'2-digit',minute:'2-digit',timeZoneName:'short'}).format(new Date(value));
  async function display(){
    if(!manifest)return;const item=manifest.basins.find(b=>b.id===basin),graphic=item.images.find(g=>g.days===Number(days.value)),id=++request;
    image.hidden=true;snapshot.hidden=true;status.textContent='Loading '+item.name+' '+days.value+'-day outlook…';
    document.querySelectorAll('[data-basin]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.basin===basin)));
    const official=new URL('https://www.nhc.noaa.gov/gtwo.php');official.searchParams.set('basin',item.official_basin_id);official.searchParams.set('fdays',days.value);document.querySelector('#tropical-official').href=official.href;
    const url=mode.value==='official'?new URL(graphic.source_url):new URL(graphic.image_filename,base);url.searchParams.set('v',mode.value==='official'?Date.now():graphic.image_sha256);
    try{const loaded=new Image();await new Promise((resolve,reject)=>{loaded.onload=resolve;loaded.onerror=()=>reject(new Error('The outlook graphic could not be loaded. Use the official outlook link or try the published snapshot.'));loaded.src=url;});if(id!==request)return;
      image.src=url;image.alt=item.name+' official '+days.value+'-day tropical cyclone formation outlook. Read the issuance printed on the graphic.';image.hidden=false;
      if(mode.value==='official'){status.textContent='Direct NHC/CPHC image loaded '+date(new Date())+'. Issuance is printed on the graphic; the stored bulletin and system list are hidden.';return;}
      const stale=Date.now()-Date.parse(manifest.generated_at_utc)>8*3600000;
      status.textContent=(stale?'Older published snapshot. ':'Published snapshot. ')+'Fetched '+date(manifest.generated_at_utc)+'. Check the issuance on the graphic; use “Latest official graphic” for intervening updates.';
      document.querySelector('#tropical-basin-heading').textContent=item.name+' outlook.';
      document.querySelector('#tropical-snapshot-time').textContent='Snapshot '+date(manifest.generated_at_utc);
      document.querySelector('#tropical-issued').textContent='Bulletin published '+date(item.bulletin.published_at_utc||item.bulletin.issued_at_utc)+'. Official issuance is stated in the bulletin below.';
      document.querySelector('#tropical-text').textContent=item.bulletin.text;document.querySelector('#tropical-bulletin-source').href=item.bulletin.source_url;
      document.querySelector('#tropical-system-count').textContent=item.active_systems.length?item.active_systems.length+' active system'+(item.active_systems.length===1?'':'s'):'No active systems reported in this snapshot.';
      const list=document.querySelector('#tropical-system-list');list.replaceChildren();
      for(const storm of item.active_systems){const card=document.createElement('article');card.className='tropical-system';const name=document.createElement('strong');name.textContent=storm.name;const detail=document.createElement('p');detail.textContent=storm.id+(storm.classification?' · '+storm.classification:'');const link=document.createElement('a');link.textContent='Official advisory ↗';link.href=storm.advisory_url;card.append(name,detail,link);list.append(card);}snapshot.hidden=false;
    }catch(error){if(id===request){
      if(mode.value==='official'){
        mode.value='snapshot';await display();
        if(!image.hidden)status.textContent='Direct NHC image embedding was blocked or unavailable. Published snapshot '+date(manifest.generated_at_utc)+' is shown. Use the official outlook link for newer updates.';
      }else{image.hidden=true;snapshot.hidden=true;status.textContent=error.message;}
    }}
  }
  async function load(){try{const response=await fetch(base,{cache:'no-store',signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error('Published tropical outlooks are unavailable. Check the official NHC links below.');manifest=await response.json();if(!manifest.basins?.length||!Number.isFinite(Date.parse(manifest.generated_at_utc)))throw new Error('The tropical outlook metadata could not be read.');display();}catch(error){status.textContent=error.message;image.hidden=true;snapshot.hidden=true;}}
  document.querySelectorAll('[data-basin]').forEach(button=>button.addEventListener('click',()=>{basin=button.dataset.basin;display();}));
  days.addEventListener('change',display);mode.addEventListener('change',display);
  document.querySelector('#tropical-refresh').addEventListener('click',()=>mode.value==='official'?display():load());load();
})();
