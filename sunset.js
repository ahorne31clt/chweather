// Read only the forecast produced by the pipeline; never invent fallback data.
document.querySelectorAll('[data-sunset-manifest]').forEach(async section => {
  const status = section.querySelector('.sunset-status');
  const image = section.querySelector('.sunset-image');
  const imageLink = section.querySelector('.sunset-image-link');
  image.addEventListener('error', () => {
    status.textContent = 'The forecast image is unavailable. Please check back after the next successful update.';
    imageLink.hidden = true;
  });
  try {
    const manifestUrl = new URL(section.dataset.sunsetManifest, document.baseURI);
    const response = await fetch(manifestUrl, { cache: 'no-store' });
    if (!response.ok) throw new Error('Forecast metadata unavailable');
    const data = await response.json();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(data.forecast_valid_date) ||
        data.image_filename !== 'latest.png' || !Array.isArray(data.top_locations) ||
        !Number.isFinite(Date.parse(data.model_run)) || !Number.isFinite(Date.parse(data.generated_at_utc))) {
      throw new Error('Invalid forecast metadata');
    }
    const today = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit'
    }).format(new Date());
    const isToday = data.forecast_valid_date === today;
    status.textContent = isToday
      ? 'Latest outlook · valid for this evening. Daily update target: 8 a.m. Eastern.'
      : `This outlook is valid for ${data.forecast_valid_date}, not today. A newer forecast is not available yet.`;
    status.classList.toggle('sunset-stale', !isToday);
    section.querySelector('[data-sunset-date]').textContent = data.forecast_valid_date;
    section.querySelector('[data-sunset-run]').textContent = data.model_run.replace('T', ' ').replace('Z', ' UTC');
    section.querySelector('[data-sunset-generated]').textContent = data.generated_at_utc.replace('T', ' ').replace('Z', ' UTC');
    section.querySelector('.sunset-metadata').hidden = false;
    const url = new URL(data.image_filename, manifestUrl);
    url.searchParams.set('v', data.image_sha256 || data.generated_at_utc);
    image.src = url.href;
    image.alt = `Experimental sunset potential for ${data.forecast_valid_date}, using GFS run ${data.model_run}. Highlighted areas: ${data.top_locations.map(p => p.label).join('; ')}.`;
    imageLink.href = url.href;
    const picks = section.querySelector('.sunset-picks');
    for (const pick of data.top_locations) {
      const article = document.createElement('article');
      const rank = document.createElement('p'); rank.className = 'eyebrow';
      rank.textContent = `0${pick.rank} / RELATIVE PICK`;
      const heading = document.createElement('h3'); heading.textContent = pick.label;
      const score = document.createElement('p'); score.textContent = `Potential index: ${pick.score} / 100`;
      const location = document.createElement('p'); location.className = 'muted';
      location.textContent = `${pick.latitude.toFixed(2)}°N, ${Math.abs(pick.longitude).toFixed(2)}°W · ${pick.nearest_city_distance_km} km from named city`;
      article.append(rank, heading, score, location); picks.append(article);
    }
  } catch (error) {
    status.textContent = 'Forecast metadata is unavailable. Check the valid date printed on the graphic; this image may be from an earlier update.';
    status.classList.add('sunset-stale');
  }
});
