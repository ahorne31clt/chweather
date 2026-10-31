import { build } from 'esbuild';
import { mkdir,copyFile,readdir,readFile,writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.dirname(here),vendor=path.join(root,'assets/vendor');
await mkdir(vendor,{recursive:true});
await build({entryPoints:[path.join(here,'worker.mjs')],bundle:true,format:'esm',target:'es2022',platform:'browser',minify:true,
  outfile:path.join(vendor,'radar-worker.js'),loader:{'.wasm':'file'},assetNames:'radar-[name]-[hash]',publicPath:'./',alias:{'node:zlib':path.join(here,'zlib.mjs')},external:['fs','path','crypto'],legalComments:'eof'});
await copyFile(path.join(here,'node_modules/leaflet/dist/leaflet.js'),path.join(vendor,'leaflet.js'));
await copyFile(path.join(here,'node_modules/leaflet/dist/leaflet.css'),path.join(vendor,'leaflet.css'));
await mkdir(path.join(vendor,'images'),{recursive:true});
for(const file of await readdir(path.join(here,'node_modules/leaflet/dist/images')))await copyFile(path.join(here,'node_modules/leaflet/dist/images',file),path.join(vendor,'images',file));
let notices='# Radar third-party licenses\n\nBundled versions are pinned in radar/package-lock.json.\n';
for(const name of ['leaflet','nexrad-level-2-data','@foxglove/wasm-bz2','fast-png','pako','iobuffer','tslib']){
  const dir=path.join(here,'node_modules',name),files=await readdir(dir).catch(()=>[]);
  for(const file of files.filter(n=>/^(license|copying)/i.test(n))){try{notices+=`\n## ${name} / ${file}\n\n`+await readFile(path.join(dir,file),'utf8')+'\n';}catch{}}
}
notices+='\n## bzip2\n\n'+await readFile(path.join(here,'BZIP2-LICENSE.txt'),'utf8');
await copyFile(path.join(here,'palettes.mjs'),path.join(root,'assets/radar-palettes.js'));
await writeFile(path.join(vendor,'RADAR-LICENSES.md'),notices);
console.log('Built local radar worker, WASM and map assets.');
