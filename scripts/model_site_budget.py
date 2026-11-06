"""Fit a static export quickly: optional annotations first, one resize pass last."""
from pathlib import Path
import hashlib,json,time


def fit_model_graphics(root,budget=900_000_000):
    root=Path(root).resolve();folder=root/'generated/models';manifest=folder/'latest.json'
    if budget<=0:raise ValueError('Publication budget must be positive')
    sizes={p:p.stat().st_size for p in root.rglob('*') if p.is_file()}
    total=sum(sizes.values());started=time.monotonic()
    categories={}
    for p,n in sizes.items():
        name=p.relative_to(root).as_posix()
        category=('model smoothing layers' if name.startswith('generated/models/') and '-overlay.' in p.name else
            'model graphics' if name.startswith('generated/models/') and p.suffix in ('.png','.webp') else
            'model numeric data/manifests' if name.startswith('generated/models/') else 'other website files')
        categories[category]=categories.get(category,0)+n
    print('Publication bytes: '+', '.join(f'{k}={v:,}' for k,v in categories.items())+f'; total={total:,}; budget={budget:,}',flush=True)
    if total<=budget:return dict(bytes=total,resized=False,omitted_smoothing_layers=0)
    if not manifest.is_file():raise ValueError('Site exceeds publication budget without a model manifest')
    state=json.loads(manifest.read_text(encoding='utf-8'));entries=[];primaries=set();overlays={}
    def asset(name):
        if not isinstance(name,str) or Path(name).name!=name or '/' in name or '\\' in name or Path(name).suffix not in ('.png','.webp'):raise ValueError('Unsafe model graphic filename')
        path=(folder/name).resolve()
        if path.parent!=folder.resolve() or not path.is_file():raise ValueError('Missing or escaped model graphic')
        return path
    for model in state.get('models',[]):
        for frame in model.get('frames',[]):
            if frame.get('image_filename'):primaries.add(asset(frame['image_filename']))
            if frame.get('overlay_filename'):
                path=asset(frame['overlay_filename'])
                overlays.setdefault(path,dict(important=False,entries=[]))['entries'].append(frame)
            for product,entry in frame.get('images',{}).items():
                entries.append(entry)
                if entry.get('image_filename'):primaries.add(asset(entry['image_filename']))
                if entry.get('overlay_filename'):
                    path=asset(entry['overlay_filename'])
                    # Preserve the most useful coarse-grid smoothing until other layers are exhausted.
                    important=model.get('id')=='gfs' and product in ('temp2m','dewpoint2m')
                    record=overlays.setdefault(path,dict(important=False,entries=[]))
                    record['important']|=important;record['entries'].append(entry)
    if primaries&set(overlays):raise ValueError('A smoothing layer aliases a forecast graphic')
    fixed=total-sum(sizes[path] for path in primaries|set(overlays))
    if fixed>budget:raise ValueError(f'Non-image data alone use {fixed:,} bytes, exceeding the budget. Image resizing cannot solve this.')
    target=budget-min(16384,max(512,budget//1000));dropped=0;hashes={};resized=0
    ordered=sorted(overlays,key=lambda path:(overlays[path]['important'],-sizes.get(path,0),path.name))
    def drop(paths):
        nonlocal total,dropped
        for path in paths:
            if total<=target:break
            if not path.exists():continue
            for entry in overlays[path]['entries']:
                entry.pop('overlay_filename',None);entry.pop('overlay_sha256',None)
                entry['smoothing_available']=False
            # Resolved, bounded files inside this fresh export only; source artifacts remain intact.
            path.unlink();total-=sizes[path];dropped+=1
    drop([path for path in ordered if not overlays[path]['important']])
    print(f'Omitted {dropped} optional smoothing layers; estimated export {total:,} bytes. Forecast maps/hours/numerics retained.',flush=True)
    if total>target:
        from PIL import Image
        from concurrent.futures import ThreadPoolExecutor
        candidates=sorted(primaries|{p for p in overlays if p.exists()},key=lambda p:-sizes[p])
        image_bytes=sum(sizes[p] for p in candidates)
        with Image.open(candidates[0]) as sample:source_width=sample.width
        ratio=max(.01,min(1,(target-fixed)/max(1,image_bytes)))
        width=max(640,min(960,round(source_width*ratio**1.4/160)*160))
        print(f'One bounded graphics pass, up to {len(candidates)} files, target width {width}; two workers.',flush=True)
        def compact(path):
            with Image.open(path) as source:
                if source.width<=width:return path,None,None
                mode='RGBA' if path in overlays else 'RGB'
                image=source.convert(mode).resize((width,round(source.height*width/source.width)),Image.Resampling.LANCZOS)
                image=image.quantize(colors=256,method=Image.Quantize.FASTOCTREE)
            temporary=path.with_name(path.name+'.resize')
            try:
                if path.suffix=='.webp':image.convert(mode).save(temporary,format='WEBP',lossless=True,method=0)
                else:image.save(temporary,format='PNG',compress_level=3)
                amount=temporary.stat().st_size
                if amount<sizes[path]:
                    temporary.replace(path)
                    return path,amount,hashlib.sha256(path.read_bytes()).hexdigest()
                return path,None,None
            finally:temporary.unlink(missing_ok=True)
        done=0
        with ThreadPoolExecutor(max_workers=2) as workers:
            for start in range(0,len(candidates),64):
                for path,amount,digest in workers.map(compact,candidates[start:start+64]):
                    if amount is not None:
                        total+=amount-sizes[path];sizes[path]=amount;hashes[path.name]=digest;resized+=1
                    done+=1
                print(f'Graphics {done}/{len(candidates)}; estimated export {total:,} bytes; elapsed {time.monotonic()-started:.0f}s',flush=True)
                if total<=target:break
    if total>target:drop([path for path in ordered if overlays[path]['important']])
    if total>target:raise ValueError(f'Site remains {total:,} bytes after removing optional layers and one resize pass. Forecast frames/numeric data were not removed; additional asset storage is needed.')
    for model in state.get('models',[]):
        for frame in model.get('frames',[]):
            for entry in [frame]+list(frame.get('images',{}).values()):
                for key,hashkey in [('image_filename','image_sha256'),('overlay_filename','overlay_sha256')]:
                    if entry.get(key) in hashes:entry[hashkey]=hashes[entry[key]]
    state['publication_graphics']=dict(resized_images=resized,omitted_smoothing_layers=dropped,
        note='Optional smoothing layers omitted where necessary; some display images compacted. All forecast hours and numerical data retained.')
    manifest.write_text(json.dumps(state,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    total=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if total>budget:raise ValueError('Final manifest pushed export beyond its byte budget')
    print(f'Publication ready: {total:,} bytes; {resized} resized graphics; {dropped} omitted optional smoothing layers; {time.monotonic()-started:.1f}s',flush=True)
    return dict(bytes=total,resized=bool(resized),omitted_smoothing_layers=dropped,max_width=width if resized else None)
