import test from 'node:test';
import assert from 'node:assert/strict';
import {encode} from 'fast-png';
globalThis.self={};
const {decodeMRMS}=await import('./worker.mjs');
function fixture({packing=41,parameter=2,bitmap=255}={}){
 const section=(id,length)=>{const b=new Uint8Array(length);new DataView(b.buffer).setUint32(0,length);b[4]=id;return b;};
 const one=section(1,21),v1=new DataView(one.buffer);v1.setUint16(12,2026);one.set([10,30,12,0,0],14);
 const three=section(3,72),v3=new DataView(three.buffer);v3.setUint32(30,2);v3.setUint32(34,2);v3.setUint32(46,35000000);v3.setUint32(50,280000000);v3.setUint32(55,34000000);v3.setUint32(59,281000000);
 const four=section(4,34);four[9]=6;four[10]=parameter;
 const five=section(5,21),v5=new DataView(five.buffer);v5.setUint16(9,packing);v5.setFloat32(11,-30);v5.setUint16(15,0x8001);v5.setUint16(17,1);five[19]=16;
 const six=section(6,6);six[5]=bitmap;
 const png=encode({width:2,height:2,depth:16,channels:1,data:new Uint16Array([0,60,568,65535])});const seven=section(7,png.length+5);seven.set(png,5);
 const parts=[one,three,four,five,six,seven],length=20+parts.reduce((a,b)=>a+b.length,0),bytes=new Uint8Array(length),view=new DataView(bytes.buffer);bytes.set([71,82,73,66,0,0,209,2]);view.setBigUint64(8,BigInt(length));let offset=16;for(const p of parts){bytes.set(p,offset);offset+=p.length;}bytes.set([55,55,55,55],offset);return bytes.buffer;
}
test('MRMS preserves 16-bit samples, signed scaling, geography and UTC',()=>{
 const result=decodeMRMS(fixture(),'qpe1');assert.equal(result.data[3],65535);assert.equal(result.binary,-1);assert.equal(result.decimal,1);assert.equal((result.reference+result.data[2]*2**result.binary)*10**-result.decimal,25.400000000000002);assert.equal(result.west,-80);assert.equal(result.east,-79);assert.equal(result.north,35);assert.equal(result.time,'2026-10-30T12:00:00.000Z');
});
test('wrong product and unsupported packing/bitmap fail explicitly',()=>{
 assert.throws(()=>decodeMRMS(fixture({parameter:6}),'qpe1'),/metadata/);assert.throws(()=>decodeMRMS(fixture({packing:40}),'qpe1'),/packing/);assert.throws(()=>decodeMRMS(fixture({bitmap:0}),'qpe1'),/bitmap/);assert.throws(()=>decodeMRMS(fixture().slice(0,-1),'qpe1'),/Incomplete/);
});
