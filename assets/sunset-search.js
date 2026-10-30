// No forecast API is queried here. The score is the published CH Weather grid.
const locationSection = document.querySelector('[data-location-manifest]');
if (locationSection) {
  const status = locationSection.querySelector('.location-status');
  const results = locationSection.querySelector('.location-result');
  const matches = locationSection.querySelector('.location-matches');
  const form = locationSection.querySelector('form');
  const input = form.querySelector('input');
  let sequence = 0;
  let pending = null;
  let gridPromise;
  const radians = n => n * Math.PI / 180;
  function distance(lat, lon, y, x) {
    const a = Math.sin(radians(y-lat)/2)**2 + Math.cos(radians(lat))*Math.cos(radians(y))*Math.sin(radians(x-lon)/2)**2;
    return 6371.0088*2*Math.asin(Math.sqrt(Math.min(1,a)));
  }
  function inRing(lon, lat, ring) {
    let inside = false;
    for (let i=0,j=ring.length-1;i<ring.length;j=i++) {
      const [xi,yi] = ring[i], [xj,yj] = ring[j];
      if ((yi>lat)!==(yj>lat) && lon < (xj-xi)*(lat-yi)/(yj-yi)+xi) inside=!inside;
    }
    return inside;
  }
  function onLand(lon, lat, geometry) {
    const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
    return polygons.some(p => inRing(lon,lat,p[0]) && !p.slice(1).some(hole=>inRing(lon,lat,hole)));
  }
  async function loadGrid() {
    if (!gridPromise) gridPromise = (async () => {
      const manifestURL = new URL(locationSection.dataset.locationManifest,document.baseURI);
      const response = await fetch(manifestURL,{cache:'no-store',signal:AbortSignal.timeout(15000)});
      if (!response.ok) throw new Error('Forecast metadata could not be loaded. Please try again later.');
      const meta = await response.json();
      if (meta.lookup_filename !== 'lookup.json') throw new Error('Location lookup is not available for this forecast yet.');
      const url = new URL('lookup.json',manifestURL); url.searchParams.set('v',meta.lookup_sha256 || meta.generated_at_utc);
      const gridResponse = await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(15000)});
      if (!gridResponse.ok) throw new Error('The sunset lookup grid is unavailable. Please try again later.');
      const grid = await gridResponse.json();
      if (grid.forecast_valid_date!==meta.forecast_valid_date || grid.model_run!==meta.model_run || grid.image_sha256!==meta.image_sha256) {
        throw new Error('The forecast is updating. Refresh this page in a moment.');
      }
      return grid;
    })().catch(error=>{gridPromise=null;throw error;});
    return gridPromise;
  }
  function addText(parent, tag, text, className) {
    const element = document.createElement(tag); element.textContent=text;
    if (className) element.className=className;
    parent.append(element); return element;
  }
  async function showPoint(point, requestID) {
    try {
      status.textContent='Reading your location from the latest sunset grid…';
      const grid = await loadGrid();
      if (requestID!==sequence) return;
      const {latitude:lat,longitude:lon} = point;
      if (!Number.isFinite(lat)||!Number.isFinite(lon)||!onLand(lon,lat,grid.land_geometry)) {
        throw new Error('This outlook covers land in the contiguous United States. Please choose a location within that area.');
      }
      const row=Math.round((lat-grid.latitudes[0])/grid.grid_degrees);
      const col=Math.round((lon-grid.longitudes[0])/grid.grid_degrees);
      let nearest;
      for (let dy=-1;dy<=1;dy++) for (let dx=-1;dx<=1;dx++) {
        const y=row+dy,x=col+dx;
        if (grid.scores[y]?.[x] == null) continue;
        const km=distance(lat,lon,grid.latitudes[y],grid.longitudes[x]);
        if (!nearest || km<nearest.km) nearest={y,x,km};
      }
      if (!nearest || nearest.km>35) throw new Error('No nearby land grid point is available for this location. Try a nearby inland location.');
      const value=grid.scores[nearest.y][nearest.x];
      const category=['Limited','Fair','Good','Very good','Excellent'][Math.min(4,Math.floor(value/20))];
      const minutes=grid.sunset_minutes_utc[nearest.y][nearest.x];
      const sunset=new Date(Date.parse(grid.forecast_valid_date+'T00:00:00Z')+minutes*60000);
      const timezone=point.timezone;
      const timeText = timezone ? new Intl.DateTimeFormat('en-US',{timeZone:timezone,hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(sunset) : sunset.toISOString().slice(11,16)+' UTC';
      results.replaceChildren();
      addText(results,'p',grid.forecast_valid_date+' / EXPERIMENTAL SUNSET POTENTIAL','eyebrow');
      addText(results,'h3',point.name);
      addText(results,'p',`${value} / 100 · ${category}`,'location-score');
      addText(results,'p',`Approximate sunset: ${timeText}. Valid evening: ${grid.forecast_valid_date}.`);
      addText(results,'p',`GFS run ${grid.model_run.replace('T',' ')} · Generated ${grid.generated_at_utc.replace('T',' ')}`,'muted');
      addText(results,'p',`Nearest 0.25° grid point: ${grid.latitudes[nearest.y].toFixed(2)}°N, ${Math.abs(grid.longitudes[nearest.x]).toFixed(2)}°W, ${nearest.km.toFixed(1)} km from your location. This index is not a probability or a guarantee of color.`,'source-note');
      const today = new Intl.DateTimeFormat('en-CA',{timeZone:timezone||'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
      if (grid.forecast_valid_date!==today) addText(results,'p','This forecast is dated '+grid.forecast_valid_date+', not today. A newer forecast is not available yet.','sunset-status sunset-stale');
      results.hidden=false;
      status.textContent='Showing the published outlook for '+point.name+'.';
    } catch(error) {
      if (requestID!==sequence) return;
      results.hidden=true;status.textContent=error.message;
    }
  }
  form.addEventListener('submit',async event=>{
    event.preventDefault(); const id=++sequence;
    pending?.abort();pending=new AbortController();results.hidden=true;matches.replaceChildren();
    const query=input.value.trim();
    const coordinates=query.match(/^(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)$/);
    if (coordinates) return showPoint({name:query,latitude:Number(coordinates[1]),longitude:Number(coordinates[2])},id);
    if (query.length<2) {status.textContent='Enter a city and state, ZIP code, or latitude, longitude.';return;}
    status.textContent='Finding matching US locations…';
    try {
      const url=new URL('https://geocoding-api.open-meteo.com/v1/search');
      url.search=new URLSearchParams({name:query,count:8,language:'en',format:'json',countryCode:'US'});
      const response=await fetch(url,{signal:AbortSignal.any([pending.signal,AbortSignal.timeout(15000)])});
      if (!response.ok) throw new Error('Location search is temporarily unavailable. You can still enter latitude, longitude.');
      const data=await response.json();if (id!==sequence)return;
      const points=(data.results||[]).filter(p=>p.country_code==='US');
      if (!points.length) {status.textContent='No matching US location found. Try a city and state, ZIP code, or coordinates.';return;}
      status.textContent='Choose your location:';
      points.forEach(point=>{
        const name=[point.name,point.admin1].filter(Boolean).join(', ');
        const button=addText(matches,'button',name,'button');button.type='button';
        button.addEventListener('click',()=>{matches.replaceChildren();showPoint({...point,name},id);});
      });
    } catch(error) {if (id===sequence && error.name!=='AbortError') status.textContent=error.message;}
  });
  locationSection.querySelector('[data-use-location]').addEventListener('click',()=>{
    const id=++sequence;pending?.abort();matches.replaceChildren();results.hidden=true;
    if (!navigator.geolocation) {status.textContent='Geolocation is unavailable. Search for a city or enter coordinates instead.';return;}
    status.textContent='Waiting for your browser’s location permission…';
    navigator.geolocation.getCurrentPosition(position=>{
      if (id===sequence) showPoint({name:'Your location',latitude:position.coords.latitude,longitude:position.coords.longitude},id);
    },()=>{if(id===sequence)status.textContent='Your location could not be obtained. Search for a city or enter coordinates instead.';},
    {enableHighAccuracy:false,timeout:12000,maximumAge:300000});
  });
  // A visitor can explicitly open the sunset outlook from their NWS forecast.
  const params=new URLSearchParams(location.search);
  if(params.has('lat')&&params.has('lon')) {
    const latitude=Number(params.get('lat')),longitude=Number(params.get('lon'));
    if(Number.isFinite(latitude)&&Number.isFinite(longitude)&&Math.abs(latitude)<=90&&Math.abs(longitude)<=180) {
      let timezone=params.get('tz')||undefined;
      try {if(timezone)new Intl.DateTimeFormat('en-US',{timeZone:timezone});} catch {timezone=undefined;}
      input.value=latitude.toFixed(4)+', '+longitude.toFixed(4);
      showPoint({name:(params.get('place')||input.value).slice(0,120),latitude,longitude,timezone},++sequence);
    }
  }
}
