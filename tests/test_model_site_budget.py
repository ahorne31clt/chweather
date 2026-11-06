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


def test_optional_layers_go_before_forecast_frames_and_preserve_gfs_temperature(tmp_path):
    folder=tmp_path/'generated/models';folder.mkdir(parents=True)
    image=folder/'gfs-map.webp'
    Image.fromarray(np.random.default_rng(2).integers(0,256,(180,320,3),dtype='uint8')).save(image,lossless=True)
    digest=hashlib.sha256(image.read_bytes()).hexdigest()
    for name in ['temp-overlay.webp','cin-overlay.webp']:(folder/name).write_bytes(b'optional layer'*15000)
    (folder/'values.bin.gz').write_bytes(b'forecast numbers')
    frame={'hour':12,'image_filename':image.name,'image_sha256':digest,'overlay_filename':'cin-overlay.webp','images':{
        'temp2m':{'image_filename':image.name,'image_sha256':digest,'overlay_filename':'temp-overlay.webp'},
        'cin':{'image_filename':image.name,'image_sha256':digest,'overlay_filename':'cin-overlay.webp'}}}
    manifest=folder/'latest.json';manifest.write_text(json.dumps({'models':[{'id':'gfs','frames':[frame]}]}))
    initial=sum(p.stat().st_size for p in tmp_path.rglob('*') if p.is_file())
    result=fit_model_graphics(tmp_path,initial-100000)
    state=json.loads(manifest.read_text());after=state['models'][0]['frames'][0]
    assert result['omitted_smoothing_layers']==1
    assert not result['resized']
    assert after['hour']==12 and image.exists()
    assert hashlib.sha256(image.read_bytes()).hexdigest()==digest
    assert after['images']['temp2m']['overlay_filename']=='temp-overlay.webp'
    assert 'overlay_filename' not in after['images']['cin']
    assert 'overlay_filename' not in after
    assert not (folder/'cin-overlay.webp').exists()
    assert (folder/'values.bin.gz').read_bytes()==b'forecast numbers'


def test_path_escape_is_rejected_without_deleting_external_file(tmp_path):
    import pytest
    folder=tmp_path/'generated/models';folder.mkdir(parents=True)
    outside=tmp_path/'outside.webp';outside.write_bytes(b'preserve'*1000)
    (folder/'latest.json').write_text(json.dumps({'models':[{'frames':[{'images':{'cin':{'overlay_filename':'../../outside.webp'}}}]}]}))
    with pytest.raises(ValueError,match='Unsafe'):fit_model_graphics(tmp_path,1000)
    assert outside.exists()
