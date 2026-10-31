import Level2Radar from 'nexrad-level-2-data';
import { decode as decodePNG } from 'fast-png';
import { LEVEL2,MRMS,palette } from './palettes.mjs';

let volume,grid;
const R=6371.0088,rad=Math.PI/180;
const merc=lat=>Math.log(Math.tan(Math.PI/4+lat*rad/2));
const inv=value=>(2*Math.atan(Math.exp(value))-Math.PI/2)/rad;
const scanTime=(days,ms)=>new Date((days-1)*86400000+ms).toISOString();
const sign16=value=>value&32768?-(value&32767):value;
const sign32=value=>value>=2147483648?-(value-2147483648):value;

function metadata(){
 const elevations=volume.listElevations().map(id=>{
  const rays=volume.data[id],fields=Object.entries(LEVEL2).filter(([,s])=>rays.some(r=>(r.record[s.key]||r[s.key])?.moment_data?.length)).map(([key])=>key);
  return {id,angle:rays[0]?.record.elevation_angle,fields};
 }).filter(e=>Number.isFinite(e.angle)&&e.fields.length);
 if(!elevations.length)throw new Error('No supported Level II sweeps in this volume.');
 const first=volume.data[elevations[0].id].find(r=>r.record.volume)?.record.volume;
 if(!first)throw new Error('Missing Level II site location.');
 return {site:volume.header.ICAO,time:scanTime(volume.header.modified_julian_date,volume.header.milliseconds),latitude:first.latitude,longitude:first.longitude,elevations,truncated:volume.isTruncated};
}

async function raster(values,width,height,bounds,spec,extra){
 const rgba=new Uint8ClampedArray(width*height*4),probeWidth=400,probeHeight=Math.round(height/width*400),probe=new Float32Array(probeWidth*probeHeight).fill(NaN),color=palette(spec);
 let count=0;
 for(let y=0;y<height;y++)for(let x=0;x<width;x++){
  const i=y*width+x,value=values(y,x);
  if(Number.isFinite(value)){count++;const c=color(value);if((spec.hours||spec.unit==='in/hr')&&value===0)c[3]=0;rgba.set(c,i*4);}
  if(x%4===0&&y%4===0){const ix=Math.floor(x/4),iy=Math.floor(y/4);if(ix<probeWidth&&iy<probeHeight)probe[iy*probeWidth+ix]=Number.isFinite(value)?value:NaN;}
 }
 const canvas=new OffscreenCanvas(width,height);canvas.getContext('2d').putImageData(new ImageData(rgba,width,height),0,0);
 return {blob:await canvas.convertToBlob({type:'image/png'}),bounds,probe:probe.buffer,probeWidth,probeHeight,count,...extra};
}

async function renderLevel2(message){
 if(!volume)throw new Error('No Level II volume loaded.');
 const info=metadata(),spec=LEVEL2[message.product],sweep=info.elevations.find(e=>e.id===message.elevation&&e.fields.includes(message.product));
 if(!spec||!sweep)throw new Error('This moment is not available in the selected sweep.');
 const rays=volume.data[sweep.id].map(r=>({record:r.record,data:r.record[spec.key]||r[spec.key]})).filter(r=>r.data?.moment_data?.length);
 if(!rays.length)throw new Error('No rays for this moment.');
 const bins=new Int16Array(3600).fill(-1),errors=new Float32Array(3600).fill(1000);
 rays.forEach((ray,index)=>{const az=ray.record.azimuth;
  for(let delta=-7;delta<=7;delta++){const bin=(Math.round(az*10)+delta+3600)%3600,diff=Math.abs(((bin/10-az+540)%360)-180);if(diff<=.7&&diff<errors[bin]){bins[bin]=index;errors[bin]=diff;}}
 });
 const range=message.range,lat=info.latitude,lon=info.longitude,bounds=[lat-range/111.2,lon-range/(111.2*Math.cos(lat*rad)),lat+range/111.2,lon+range/(111.2*Math.cos(lat*rad))];
 const width=1600,height=1600,north=merc(bounds[2]),south=merc(bounds[0]),latSin=[],latCos=[],lonSin=[],lonCos=[];
 for(let y=0;y<height;y++){const phi=inv(north-(north-south)*(y+.5)/height)*rad;latSin[y]=Math.sin(phi);latCos[y]=Math.cos(phi);}
 for(let x=0;x<width;x++){const d=(bounds[1]+(bounds[3]-bounds[1])*(x+.5)/width-lon)*rad;lonSin[x]=Math.sin(d);lonCos[x]=Math.cos(d);}
 const sin0=Math.sin(lat*rad),cos0=Math.cos(lat*rad),angle=sweep.angle*rad,earth=R*4/3;
 return raster((y,x)=>{
  const distance=R*Math.acos(Math.max(-1,Math.min(1,sin0*latSin[y]+cos0*latCos[y]*lonCos[x])));
  if(distance>range)return NaN;
  const bearing=(Math.atan2(lonSin[x]*latCos[y],cos0*latSin[y]-sin0*latCos[y]*lonCos[x])/rad+360)%360;
  const index=bins[Math.round(bearing*10)%3600];if(index<0)return NaN;
  const data=rays[index].data,t=Math.tan(distance/earth),slant=earth*t/(Math.cos(angle)-Math.sin(angle)*t);
  const gate=Math.round((slant-data.first_gate)/data.gate_size);
  if(gate<0||gate>=data.moment_data.length)return NaN;
  const value=data.moment_data[gate];return value===null||!Number.isFinite(value)?NaN:value*(spec.convert||1);
 },width,height,bounds,spec,{...info,sweep:sweep.angle,product:message.product});
}

export function decodeMRMS(bytes,product){
 const raw=new Uint8Array(bytes),view=new DataView(bytes),spec=MRMS[product];
 if(!spec||raw.length<100||String.fromCharCode(...raw.slice(0,4))!=='GRIB'||raw[7]!==2||raw[6]!==209)throw new Error('Not a NOAA MRMS GRIB2 product.');
 if(Number(view.getBigUint64(8))!==raw.length)throw new Error('Incomplete MRMS GRIB2.');
 let geometry,packing,png,time,parameter;
 for(let offset=16;offset<raw.length-4;){
  const length=view.getUint32(offset),section=raw[offset+4];if(length<5||offset+length>raw.length)throw new Error('Invalid MRMS GRIB section.');
  if(section===1)time=new Date(Date.UTC(view.getUint16(offset+12),raw[offset+14]-1,raw[offset+15],raw[offset+16],raw[offset+17],raw[offset+18])).toISOString();
  if(section===3){
   if(view.getUint16(offset+12)!==0)throw new Error('Unsupported MRMS projection.');
   geometry={width:view.getUint32(offset+30),height:view.getUint32(offset+34),north:sign32(view.getUint32(offset+46))/1e6,west:(view.getUint32(offset+50)/1e6+180)%360-180,south:sign32(view.getUint32(offset+55))/1e6,east:(view.getUint32(offset+59)/1e6+180)%360-180,scan:raw[offset+71]};
  }
  if(section===4)parameter=[raw[offset+9],raw[offset+10]];
  if(section===5){if(view.getUint16(offset+9)!==41)throw new Error('Unsupported MRMS packing; no substitute image used.');packing={reference:view.getFloat32(offset+11),binary:sign16(view.getUint16(offset+15)),decimal:sign16(view.getUint16(offset+17))};}
  if(section===6&&raw[offset+5]!==255)throw new Error('Unsupported MRMS bitmap.');
  if(section===7)png=raw.subarray(offset+5,offset+length);
  offset+=length;
 }
 if(!geometry||!packing||!png||!time||parameter?.[0]!==spec.category||parameter?.[1]!==spec.parameter||geometry.scan!==0)throw new Error('MRMS product metadata differs from selection.');
 if(geometry.width*geometry.height>30000000)throw new Error('MRMS grid exceeds supported size.');
 const decoded=decodePNG(png,{checkCrc:true});
 if(decoded.width!==geometry.width||decoded.height!==geometry.height||decoded.channels!==1||![8,16].includes(decoded.depth))throw new Error('Invalid MRMS packed PNG.');
 return {...geometry,...packing,data:decoded.data,time,product};
}

async function renderMRMS(message){
 if(!grid)throw new Error('No MRMS grid loaded.');
 const spec=MRMS[grid.product],requested=message.bounds||[20,-130,55,-60];
 const bounds=[Math.max(20,requested[0]),Math.max(-130,requested[1]),Math.min(55,requested[2]),Math.min(-60,requested[3])];
 if(bounds[0]>=bounds[2]||bounds[1]>=bounds[3])throw new Error('MRMS selected products cover CONUS. Pan back to the contiguous US.');
 const width=1600,north=merc(bounds[2]),south=merc(bounds[0]),height=Math.max(400,Math.min(1600,Math.round(width*(north-south)/((bounds[3]-bounds[1])*rad)/4)*4));
 const dy=(grid.north-grid.south)/(grid.height-1),dx=(grid.east-grid.west)/(grid.width-1),ys=[];
 for(let y=0;y<height;y++)ys[y]=Math.round((grid.north-inv(north-(north-south)*(y+.5)/height))/dy);
 const multiplier=2**grid.binary,decimal=10**(-grid.decimal);
 return raster((y,x)=>{const row=ys[y],lon=bounds[1]+(bounds[3]-bounds[1])*(x+.5)/width,col=Math.round((lon-grid.west)/dx);
  if(row<0||col<0||row>=grid.height||col>=grid.width)return NaN;
  const value=(grid.reference+grid.data[row*grid.width+col]*multiplier)*decimal;
  if((grid.product==='composite'&&value< -50)||(grid.product!=='composite'&&value<0))return NaN;
  return value*(spec.convert||1);
 },width,height,bounds,spec,{time:grid.time,product:grid.product});
}

self.onmessage=async({data:message})=>{
 try{
  let result;
  if(message.type==='loadLevel2'){
   grid=null;volume=new Level2Radar(new Uint8Array(message.buffer),{logger:false});
   if(volume.isTruncated)throw new Error('Incomplete Level II volume; select another completed scan.');
   result=metadata();if(result.site!==message.site)throw new Error('Level II site does not match selection.');
  }else if(message.type==='renderLevel2')result=await renderLevel2(message);
  else if(message.type==='loadMRMS'){
   volume=null;const raw=await new Response(new Blob([message.buffer]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
   if(raw.byteLength>80000000)throw new Error('MRMS GRIB exceeds supported size.');grid=decodeMRMS(raw,message.product);result={time:grid.time};
  }else if(message.type==='renderMRMS')result=await renderMRMS(message);
  else throw new Error('Unknown radar operation.');
  self.postMessage({id:message.id,result},result.probe?[result.probe]:[]);
 }catch(error){self.postMessage({id:message.id,error:error.message||'Radar decoding failed.'});}
};

