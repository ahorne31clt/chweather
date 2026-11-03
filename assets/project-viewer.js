(()=>{
 if(['localhost','127.0.0.1'].includes(location.hostname))for(const link of document.querySelectorAll('[data-pdf-local]'))link.href=link.dataset.pdfLocal;
 const viewer=document.querySelector('[data-slide-manifest]');if(!viewer)return;
 const image=viewer.querySelector('img'),caption=viewer.querySelector('figcaption'),status=viewer.querySelector('[role=status]'),select=viewer.querySelector('select'),previous=viewer.querySelector('[data-slide-previous]'),next=viewer.querySelector('[data-slide-next]');let metadata,index=0;
 const manifest=new URL(viewer.dataset.slideManifest,document.baseURI);
 function display(number){
  index=Math.max(0,Math.min(metadata.slides.length-1,number));const slide=metadata.slides[index];
  if(!/^(slide-\d{2}|map-preview)\.webp$/.test(slide.image_filename))throw new Error('Invalid slide filename');
  image.src=new URL(slide.image_filename,manifest);image.alt=viewer.dataset.projectName+', slide '+slide.number+' of '+metadata.slide_count+'. '+slide.caption;caption.textContent='Slide '+slide.number+' / '+metadata.slide_count+' — '+slide.caption;select.value=index;
  previous.disabled=index===0;next.disabled=index===metadata.slides.length-1;status.textContent='Showing slide '+slide.number+' of '+metadata.slide_count+'. Full PDFs are available below.';
  history.replaceState(null,'',location.pathname+'#slide-'+slide.number);
  for(const neighbor of [index-1,index+1])if(metadata.slides[neighbor]){const preload=new Image();preload.src=new URL(metadata.slides[neighbor].image_filename,manifest);}
 }
 (async()=>{try{
  const response=await fetch(manifest);if(!response.ok)throw new Error('Slide previews could not be loaded. You can still open the PDF below.');metadata=await response.json();if(!metadata.slides?.length)throw new Error('No slide previews are available. Open the PDF below.');
  for(const [i,slide]of metadata.slides.entries()){const option=document.createElement('option');option.value=i;option.textContent=slide.number+' / '+slide.caption;select.append(option);}select.disabled=false;
  previous.onclick=()=>display(index-1);next.onclick=()=>display(index+1);select.onchange=()=>display(Number(select.value));
  for(const button of viewer.querySelectorAll('[data-slide]')){button.disabled=false;button.onclick=()=>display(Number(button.dataset.slide)-1);}
  viewer.addEventListener('keydown',event=>{if(event.target.matches('select,input')||event.altKey||event.ctrlKey||event.metaKey)return;if(event.key==='ArrowLeft'){event.preventDefault();display(index-1);}if(event.key==='ArrowRight'){event.preventDefault();display(index+1);}});
  const match=location.hash.match(/^#slide-(\d+)$/);display(match?Number(match[1])-1:0);
 }catch(error){status.textContent=error.message;}})();
 image.addEventListener('error',()=>{status.textContent='This slide preview could not be loaded. The full PDF is available below.';});
})();
