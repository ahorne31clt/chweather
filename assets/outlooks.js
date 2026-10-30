const browserSection = document.querySelector('[data-weather-manifest]');
if (browserSection) {
  let type='weather', region='nc', manifest;
  const panel=browserSection.querySelector('.outlook-products');
  const status=browserSection.querySelector('.outlook-status');
  const explanations={
    weather:'Official NWS daytime high temperatures, with the matching 12-hour precipitation chance at selected cities. CH Weather graphic presentation.',
    spc:'Official SPC categorical outlooks, with their original risk areas, categories, issuance, and valid times. These are snapshots; check SPC for newer issuances.',
    rain:'Daily-updated chance of measurable precipitation during the exact 12-hour interval shown. Includes rain or frozen precipitation; this is not a 24-hour probability.',
    foliage:'Explore Fall’s published, dated foliage-model estimate. Not a direct observation or a locally generated peak-color prediction.'
  };
  function text(parent,tag,value,className) {
    const element=document.createElement(tag);element.textContent=value;
    if(className)element.className=className;
    parent.append(element);return element;
  }
  function renderProducts() {
    if(!manifest)return;
    panel.replaceChildren();
    browserSection.querySelector('.outlook-explanation').textContent=explanations[type];
    browserSection.querySelector('.outlook-regions').hidden=type==='spc';
    const products=manifest.products.filter(p=>p.type===type && (type==='spc'||p.region===region));
    status.textContent=products.length?`Showing ${products.length} ${type==='spc'?'official SPC outlooks':region==='nc'?'North Carolina product':'national product'}.`:
      type==='foliage'&&manifest.foliage_status==='out_of_season'?'Daily fall color maps are seasonal. Visit Explore Fall for source information.':'This product is unavailable. Please use the official source links below.';
    for(const product of products) {
      const article=document.createElement('article');article.className='outlook-product';
      text(article,'p',product.source+' / '+product.kind,'eyebrow');
      text(article,'h3',product.title);
      const issued=product.issued_at_utc;
      const validStart=product.valid_start_utc,validEnd=product.valid_end_utc;
      text(article,'p',product.source_date?`Foliage model date: ${product.source_date}`:`Issued ${issued.replace('T',' ')} · Valid ${validStart.replace('T',' ')} to ${validEnd.replace('T',' ')}`,'outlook-valid');
      const expired=product.source_date?product.source_date!==new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()):Date.parse(validEnd)<=Date.now();
      if(expired)text(article,'p','This product is from an earlier date or has passed its valid interval. A newer product is not available here yet.','sunset-status sunset-stale');
      const base=new URL(browserSection.dataset.weatherManifest,document.baseURI);
      if(!/^[a-z0-9-]+\.png$/.test(product.image_filename))continue;
      const url=new URL(product.image_filename,base);url.searchParams.set('v',product.image_sha256||product.generated_at_utc);
      const link=document.createElement('a');link.href=url.href;link.className='sunset-image-link';link.setAttribute('aria-label','Open full-resolution '+product.title);
      const image=document.createElement('img');image.src=url.href;image.width=2400;image.height=1500;image.loading='lazy';image.className='sunset-image';image.alt=product.title+', '+(product.source_date||validStart)+'; '+product.source;
      image.addEventListener('error',()=>{link.hidden=true;text(article,'p','This graphic could not be loaded. Please use the source link below.','sunset-status sunset-stale');});
      link.append(image);article.append(link);
      if(product.summary)text(article,'p',product.summary,'outlook-summary');
      if((type==='weather'||type==='rain')&&product.cities?.length) {
        const scroll=document.createElement('div');scroll.className='table-scroll';
        const table=document.createElement('table');table.className='forecast-table';
        text(table,'caption','Selected NWS forecast points · same 12-hour valid interval');
        const header=table.createTHead().insertRow();
        ['Location',...(type==='weather'?['Daytime high']:[]),'Precipitation chance'].forEach(label=>{const th=document.createElement('th');th.scope='col';th.textContent=label;header.append(th);});
        const body=table.createTBody();
        for(const city of product.cities){const row=body.insertRow();text(row,'td',city.name);if(type==='weather')text(row,'td',city.high_f==null?'Unavailable':Math.round(city.high_f)+'°F');text(row,'td',city.pop_percent==null?'Unavailable':Math.round(city.pop_percent)+'%');}
        scroll.append(table);article.append(scroll);
      }
      text(article,'p','Generated '+product.generated_at_utc.replace('T',' ')+' · Open the image for full-resolution labels.','source-note');
      const sources=document.createElement('div');sources.className='source-links';
      const sourceURL=type==='spc'?`https://www.spc.noaa.gov/products/outlook/day${product.id.slice(-1)}otlk.html`:type==='foliage'?'https://www.explorefall.com/fall-foliage-map':'https://www.weather.gov/';
      const source=text(sources,'a','Open official source ↗','text-link');source.href=sourceURL;
      const download=text(sources,'a','Open full-size graphic ↗','text-link');download.href=url.href;
      article.append(sources);panel.append(article);
    }
  }
  browserSection.querySelectorAll('[data-outlook-type]').forEach(button=>button.addEventListener('click',()=>{
    type=button.dataset.outlookType;
    browserSection.querySelectorAll('[data-outlook-type]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});
    history.replaceState(null,'','#'+type);renderProducts();
  }));
  browserSection.querySelectorAll('[data-outlook-region]').forEach(button=>button.addEventListener('click',()=>{
    region=button.dataset.outlookRegion;
    browserSection.querySelectorAll('[data-outlook-region]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});renderProducts();
  }));
  (async()=>{
    try {
      const response=await fetch(new URL(browserSection.dataset.weatherManifest,document.baseURI),{cache:'no-store',signal:AbortSignal.timeout(15000)});
      if(!response.ok)throw new Error('unavailable');manifest=await response.json();
      if(!Array.isArray(manifest.products))throw new Error('invalid');
      const initial=location.hash.slice(1);
      const button=browserSection.querySelector(`[data-outlook-type="${Object.keys(explanations).includes(initial)?initial:'weather'}"]`);
      if(Object.keys(explanations).includes(initial))button.click();
      else renderProducts();
    } catch {status.textContent='Forecast metadata is unavailable. Please use the official source links below.';}
  })();
}
