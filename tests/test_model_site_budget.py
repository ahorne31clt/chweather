import hashlib,json
import numpy as np
from PIL import Image
from scripts.model_site_budget import fit_model_graphics

def test_graphic_budget_updates_hashes_without_changing_numerics(tmp_path):
    folder=tmp_path/'generated/models';folder.mkdir(parents=True)
    pixels=np.random.default_rng(4).integers(0,256,(900,1600,3),dtype='uint8')
    image=folder/'gfs-test.webp';Image.fromarray(pixels).save(image,lossless=True)
    (folder/'values.bin.gz').write_bytes(b'unchanged numerical bytes')
    entry={'image_filename':image.name,'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest()}
    frame=dict(entry,images={'temp2m':dict(entry)})
    manifest=folder/'latest.json';manifest.write_text(json.dumps({'models':[{'frames':[frame]}]}))
    initial=sum(p.stat().st_size for p in tmp_path.rglob('*') if p.is_file())
    result=fit_model_graphics(tmp_path,int(initial*.8))
    state=json.loads(manifest.read_text())
    assert result['resized']
    assert state['models'][0]['frames'][0]['images']['temp2m']['image_sha256']==hashlib.sha256(image.read_bytes()).hexdigest()
    assert (folder/'values.bin.gz').read_bytes()==b'unchanged numerical bytes'
    assert Image.open(image).width<=1280
