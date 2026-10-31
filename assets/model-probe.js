/* Raw-value probing and display-only smoothing; no forecast values are inferred from colors. */
window.CHModelProbe=class {
  constructor(stage,map,box){
    this.stage=stage;this.map=map;this.box=box;this.epoch=0;this.cache=new Map();this.view={zoom:1,panX:0,panY:0};this.mode='off';
    this.canvas=document.createElement('canvas');this.canvas.width=2400;this.canvas.height=1350;this.canvas.className='model-smooth-canvas';this.canvas.hidden=true;this.canvas.setAttribute('aria-hidden','true');stage.insertBefore(this.canvas,box);this.position();
    this.metrics={temp2m:[['temperature2','Temperature'],['dewpoint2','Dewpoint']],dewpoint2m:[['dewpoint2','Dewpoint'],['temperature2','Temperature']],
      wind10:[['wind10','10 m wind'],['temperature2','Temperature']],rh2m:[['humidity2','Relative humidity'],['dewpoint2','Dewpoint']],
      mslp:[['pressure','MSLP'],['temperature2','Temperature']],sbcape:[['cape','Surface CAPE'],['humidity2','Relative humidity']],
      wind500:[['wind500','500 mb wind'],['height500','500 mb height']],vort500:[['vorticity500','Abs. vorticity'],['height500','500 mb height']],
      precip:[['rate','Precip rate'],['precip_type','Precip type'],['pressure','MSLP'],['thickness','1000–500 mb thickness']]};
  }
  position(){
    const {width,height}=this.stage.getBoundingClientRect(),fit=Math.min(width/2400,height/1350);
    Object.assign(this.canvas.style,{width:2400*fit+'px',height:1350*fit+'px',left:(width-2400*fit)/2+'px',top:(height-1350*fit)/2+'px',transform:`translate(${this.view.panX}px,${this.view.panY}px) scale(${this.view.zoom})`});
  }
  setView(view){this.view=view;this.position();if(this.lastPointer)this.sample(this.lastPointer);}
  load(frame,product,definition){
    this.controller?.abort();this.controller=new AbortController();this.epoch++;this.frame=frame;this.product=product;this.definition=definition;this.grid=null;this.pending=null;this.hideSmooth();
    this.box.replaceChildren();this.box.hidden=false;
    const heading=document.createElement('span');heading.className='model-readout-label';heading.textContent='MODEL VALUES / NATIVE GRID SAMPLES';this.box.append(heading);
    const values=document.createElement('div');values.className='model-probe-values';this.nodes={};
    for(const [key,label] of this.metrics[product]||[]){const cell=document.createElement('span'),name=document.createElement('span'),strong=document.createElement('strong'),unit=document.createElement('small');name.textContent=label;strong.textContent='—';cell.append(name,strong,unit);values.append(cell);this.nodes[key]={strong,unit};}this.box.append(values);
    this.help=document.createElement('small');this.help.textContent='Move over the map or tap for values.';this.box.append(this.help);
    if(this.lastPointer||this.mode!=='off')this.ensure().then(()=>{if(this.lastPointer)this.sample(this.lastPointer);if(this.mode!=='off')this.smooth();}).catch(()=>{});
  }
  async ensure(){
    if(this.grid)return this.grid;if(this.pending)return this.pending;
    const epoch=this.epoch,spec=this.frame?.readouts,controller=this.controller,signal=controller.signal;
    this.help.textContent='Loading numeric model values…';
    this.pending=(async()=>{
      if(!spec||!/^(gfs|hrrr|nam)-\d{10}-f\d{3}\.bin(\.gz)?$/.test(spec.filename))throw new Error('Numeric values are unavailable for this snapshot.');
      const url=new URL('../generated/models/'+spec.filename,document.baseURI);url.searchParams.set('v',spec.sha256);
      let grid=this.cache.get(url.href);
      if(!grid){
        const timeout=setTimeout(()=>controller.abort(),20000);let buffer;
        try{const response=await fetch(url,{signal});if(!response.ok)throw new Error('Numeric model data are temporarily unavailable.');buffer=await response.arrayBuffer();}finally{clearTimeout(timeout);}
        if(crypto.subtle&&spec.sha256){const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',buffer)),v=>v.toString(16).padStart(2,'0')).join('');if(digest!==spec.sha256)throw new Error('Numeric data could not be verified.');}
        if(spec.encoding==='gzip'){
          if(!window.DecompressionStream)throw new Error('This browser needs gzip-stream support for map values.');
          buffer=await new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
        }
        const fields=spec.field_specs||spec.fields.map(id=>({id,unit:'°F',decimals:1})),bytes=['float32-le','int32-le'].includes(spec.dtype)?4:2;
        if(fields.length>20||spec.width>1000||spec.height>600||buffer.byteLength!==spec.width*spec.height*fields.length*bytes)throw new Error('Numeric data have an unexpected format.');
        const view=new DataView(buffer);
        if(spec.dtype==='int32-le'&&spec.delta_axis==='x')for(let f=0;f<fields.length;f++)for(let row=0;row<spec.height;row++){
          const offset=(f*spec.height+row)*spec.width*4;let value=view.getInt32(offset,true);
          for(let col=1;col<spec.width;col++){value=(value+view.getInt32(offset+col*4,true))|0;view.setInt32(offset+col*4,value,true);}
        }
        grid={spec,fields,view,bytes};this.cache.set(url.href,grid);if(this.cache.size>3)this.cache.delete(this.cache.keys().next().value);
      }
      if(epoch!==this.epoch)return null;
      this.grid=grid;this.help.textContent='Raw model samples; display smoothing does not change these values.';return grid;
    })().catch(error=>{if(epoch===this.epoch&&!signal.aborted)this.help.textContent=error.message+' The graphic remains available.';throw error;});
    return this.pending;
  }
  value(key,cell){
    const grid=this.grid;if(!grid)return NaN;const index=grid.fields.findIndex(f=>f.id===key);if(index<0)return NaN;
    const offset=(index*grid.spec.width*grid.spec.height+cell)*grid.bytes;
    if(grid.spec.dtype==='int32-le'){const value=grid.view.getInt32(offset,true);return value===grid.spec.missing?NaN:value/10**grid.fields[index].decimals;}
    if(grid.bytes===4)return grid.view.getFloat32(offset,true);
    const value=grid.view.getInt16(offset,true);return value===grid.spec.missing?NaN:value/grid.spec.scale;
  }
  pointer(event){
    if(this.map.hidden||event.target.closest('button,select,a,label'))return;
    this.lastPointer={clientX:event.clientX,clientY:event.clientY};
    if(!this.grid){const epoch=this.epoch;this.ensure().then(()=>{if(epoch===this.epoch&&this.lastPointer)this.sample(this.lastPointer);}).catch(()=>{});}else this.sample(this.lastPointer);
  }
  sample(pointer){
    if(!this.grid)return;const rect=this.stage.getBoundingClientRect(),fit=Math.min(rect.width/2400,rect.height/1350),{zoom,panX,panY}=this.view;
    const px=((pointer.clientX-rect.left-rect.width/2-panX)/zoom)/fit+1200,py=((pointer.clientY-rect.top-rect.height/2-panY)/zoom)/fit+675;
    const {spec}=this.grid,col=Math.floor(px/spec.cell_pixels),row=Math.floor(py/spec.cell_pixels),inside=col>=0&&col<spec.width&&row>=0&&row<spec.height;
    for(const [key,node] of Object.entries(this.nodes)){
      const value=inside?this.value(key,row*spec.width+col):NaN,info=this.grid.fields.find(f=>f.id===key);
      node.strong.textContent=!Number.isFinite(value)?'—':key==='precip_type'?['Dry / below threshold','Rain','Snow','Freezing rain','Sleet','Mixed flags','Unclassified'][Math.round(value)]||'Unavailable':value.toFixed(info?.decimals??1);
      node.unit.textContent=info?.unit||'';
    }
  }
  hideSmooth(){this.canvas.hidden=true;this.map.style.opacity='1';}
  async setMode(mode){this.mode=mode;if(mode==='off'){this.hideSmooth();return;}try{await this.ensure();await this.smooth();}catch{this.hideSmooth();}}
  async image(url){const image=new Image();await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(new Error('Smoothing annotation layer is unavailable.'));image.src=url;});return image;}
  async smooth(){
    if(this.mode==='off'||!this.grid||!this.definition?.swatches){this.hideSmooth();return;}
    const epoch=this.epoch,entry=this.frame.images?.[this.product],filename=entry?.overlay_filename;
    if(!filename||!/^(gfs|hrrr|nam)-\d{10}-f\d{3}-[a-z0-9]+-overlay\.(png|webp)$/.test(filename)){this.help.textContent='Smoothing is unavailable for this snapshot. Raw values remain available.';return;}
    try{
      const overlayURL=new URL('../generated/models/'+filename,document.baseURI);overlayURL.searchParams.set('v',entry.overlay_sha256);
      const [original,overlay]=await Promise.all([this.image(this.map.src),this.image(overlayURL.href)]);if(epoch!==this.epoch||this.mode==='off')return;
      const key={temp2m:'temperature2',dewpoint2m:'dewpoint2',wind10:'wind10',rh2m:'humidity2',mslp:'pressure',sbcape:'cape',wind500:'wind500',vort500:'display_vorticity500'}[this.product];
      if(!this.grid.fields.some(f=>f.id===key))return;
      const {spec}=this.grid,small=document.createElement('canvas');small.width=spec.width;small.height=spec.height;
      const context=small.getContext('2d'),pixels=context.createImageData(spec.width,spec.height),levels=this.definition.levels;
      const colors=this.definition.swatches.map(hex=>[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)));
      for(let i=0;i<spec.width*spec.height;i++){
        const value=this.value(key,i);if(!Number.isFinite(value))continue;
        let bin=0;while(bin<levels.length-2&&value>=levels[bin+1])bin++;
        const color=colors[bin];pixels.data.set([...color,255],i*4);
      }
      context.putImageData(pixels,0,0);
      const ctx=this.canvas.getContext('2d');ctx.clearRect(0,0,2400,1350);ctx.drawImage(original,0,0);
      const box=spec.map_box_pixels;if(!box)throw new Error('Smoothing geometry is unavailable.');
      ctx.save();ctx.beginPath();ctx.rect(...box);ctx.clip();ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.filter='blur(3px)';ctx.drawImage(small,0,0,spec.width*spec.cell_pixels,spec.height*spec.cell_pixels);ctx.restore();
      ctx.drawImage(overlay,0,0);ctx.fillStyle='#18191A';ctx.fillRect(880,1328,660,21);ctx.font='11px Arial';ctx.textAlign='center';ctx.fillStyle='#9FB4AC';ctx.fillText('DISPLAY SMOOTHING · RAW MODEL VALUES UNCHANGED',1210,1343);
      if(epoch!==this.epoch||this.mode==='off')return;this.canvas.hidden=false;this.map.style.opacity='0';this.position();
    }catch(error){if(epoch===this.epoch){this.hideSmooth();this.help.textContent=error.message+' Native graphic shown.';}}
  }
};
