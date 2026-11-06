"""Keep a static export below its display-asset budget without altering numerics."""
from pathlib import Path
import hashlib,json

def fit_model_graphics(root,budget=900_000_000):
    root=Path(root).resolve();manifest=root/'generated/models/latest.json'
    def size():return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    total=size()
    if total<=budget or not manifest.is_file():return dict(bytes=total,resized=False)
    from PIL import Image
    state=json.loads(manifest.read_text(encoding='utf-8'));entries=[]
    for model in state.get('models',[]):
        for frame in model.get('frames',[]):
            entries.extend(frame.get('images',{}).values())
    filenames=set()
    for entry in entries:
        for key in ('image_filename','overlay_filename'):
            if name:=entry.get(key):
                if Path(name).name!=name or '/' in name or '\\' in name or Path(name).suffix not in ('.png','.webp'):raise ValueError('Unsafe model graphic filename')
                filenames.add(name)
    if not filenames:raise ValueError('Site exceeds storage budget and has no resizable model graphics')
    hashes={};width=None
    for width in (1280,1120,960):
        for name in sorted(filenames):
            path=(manifest.parent/name).resolve()
            if path.parent!=manifest.parent:raise ValueError('Graphic escaped export directory')
            with Image.open(path) as source:
                if source.width<=width:continue
                mode='RGBA' if 'overlay' in name else 'RGB'
                image=source.convert(mode).resize((width,round(source.height*width/source.width)),Image.Resampling.LANCZOS)
                image=image.quantize(colors=256,method=Image.Quantize.FASTOCTREE)
            target=path.with_name(path.name+'.resize')
            try:
                if path.suffix=='.webp':image.convert(mode).save(target,format='WEBP',lossless=True,method=2)
                else:image.save(target,format='PNG',optimize=True)
                if target.stat().st_size<path.stat().st_size:target.replace(path);hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
            finally:target.unlink(missing_ok=True)
        total=size()
        if total<=budget:break
    if total>budget:raise ValueError(f'Site is {total} bytes after compacting graphics; dedicated model image storage is required before publishing')
    for model in state.get('models',[]):
        for frame in model.get('frames',[]):
            for entry in [frame]+list(frame.get('images',{}).values()):
                for key,hashkey in [('image_filename','image_sha256'),('overlay_filename','overlay_sha256')]:
                    if entry.get(key) in hashes:entry[hashkey]=hashes[entry[key]]
    state['publication_graphics']=dict(max_width=width,note='Display graphics compacted to the static-site byte budget. Numerical grids, run times and forecast hours unchanged.')
    manifest.write_text(json.dumps(state,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(f'Compacted published model graphics: {total:,} bytes; maximum width {width}')
    return dict(bytes=total,resized=True,max_width=width)
