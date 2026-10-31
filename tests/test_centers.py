from io import BytesIO
from pathlib import Path
import importlib
import json

from PIL import Image, UnidentifiedImageError
import pytest

from centers.__main__ import products, fetch_graphic


def test_catalog_contains_official_distinct_products():
    catalog=products()
    assert len(catalog)==len({p['id'] for p in catalog})==17
    assert sum(p['center']=='wpc' for p in catalog)==7
    assert sum(p['center']=='cpc' for p in catalog)==10
    assert all(p['source_url'].startswith(('https://www.wpc.ncep.noaa.gov/','https://www.cpc.ncep.noaa.gov/')) for p in catalog)
    # Use the leading individual season, not CPC's multi-season overview mosaic.
    assert all('/long_range/lead01/' in p['source_url'] for p in catalog if p['id'].startswith('cpc-season-'))


class Response:
    headers={'Last-Modified':'Fri, 30 Oct 2026 08:00:00 GMT'}
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def raise_for_status(self):pass
    def iter_content(self,*_):yield self.payload


class Http:
    def __init__(self,payload):self.payload=payload
    def get(self,*_,**__):return Response(self.payload)


def test_graphic_conversion_preserves_pixels_and_distinguishes_file_time(tmp_path):
    stream=BytesIO();source=Image.new('RGB',(400,300),'#0b6b45');source.save(stream,format='GIF')
    path=tmp_path/'graphic.png';meta=fetch_graphic(Http(stream.getvalue()),'https://example.test/map.gif',path)
    with Image.open(path) as saved:
        assert saved.convert('RGB').tobytes()==source.tobytes()
    assert meta['source_file_modified_at_utc']=='2026-10-30T08:00:00Z'
    assert 'issued_at_utc' not in meta
    assert 'valid_start_utc' not in meta
    with pytest.raises(UnidentifiedImageError):
        fetch_graphic(Http(b'<html>service unavailable</html>'),'https://example.test',tmp_path/'bad.png')


def test_failed_refresh_keeps_entire_previous_publication(tmp_path,monkeypatch):
    pipeline=importlib.import_module('centers.__main__')
    (tmp_path/'latest.json').write_text('{"previous":true}')
    (tmp_path/'wpc-ero-1.png').write_bytes(b'previous successful graphic')
    class Session:
        def __enter__(self):return self
        def __exit__(self,*_):return False
    monkeypatch.setattr(pipeline,'session',Session)
    count=0
    def fail(http,url,path):
        nonlocal count
        count+=1
        if count==2:raise ValueError('deliberate download failure')
        Path(path).write_bytes(b'staged but never published');return {}
    monkeypatch.setattr(pipeline,'fetch_graphic',fail)
    with pytest.raises(ValueError,match='deliberate'):
        pipeline.run(tmp_path)
    assert json.loads((tmp_path/'latest.json').read_text())=={'previous':True}
    assert (tmp_path/'wpc-ero-1.png').read_bytes()==b'previous successful graphic'
