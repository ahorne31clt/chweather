import json
import re
from pathlib import Path
import pytest
from scripts import package_site as export


def test_source_export_does_not_require_any_generated_data(tmp_path,monkeypatch):
    monkeypatch.setattr(export,'ROOT',tmp_path)
    files=list(export.site_files(include_generated=False))
    assert tmp_path/'index.html' in files
    assert not any('generated' in p.parts for p in files)
    with pytest.raises(FileNotFoundError,match='Missing generated products: sunset, weather'):
        list(export.site_files())


def test_product_validation_reports_missing_models_and_airports(tmp_path,monkeypatch):
    monkeypatch.setattr(export,'ROOT',tmp_path)
    with pytest.raises(FileNotFoundError,match=r'python -m models'):
        list(export.product_files('models'))
    folder=tmp_path/'generated/models';folder.mkdir(parents=True)
    (folder/'latest.json').write_text('{"models":[]}')
    with pytest.raises(FileNotFoundError,match='airports/latest.json'):
        list(export.product_files('models'))


def test_referenced_overlay_probe_and_nested_json_are_required(tmp_path,monkeypatch):
    monkeypatch.setattr(export,'ROOT',tmp_path)
    folder=tmp_path/'generated/ensembles';folder.mkdir(parents=True)
    (folder/'latest.json').write_text(json.dumps({'images':[{'image_filename':'map.png','overlay_filename':'lines.webp','readout':{'filename':'probe.bin.gz'}}]}))
    for name in ('map.png','lines.webp'):
        (folder/name).write_bytes(b'fixture')
    with pytest.raises(FileNotFoundError,match='probe.bin.gz'):
        list(export.product_files('ensembles'))
    (folder/'probe.bin.gz').write_bytes(b'fixture')
    assert {p.name for p in export.product_files('ensembles')}=={'latest.json','map.png','lines.webp','probe.bin.gz'}
    (folder/'latest.json').write_text('{"image_filename":"../private.png"}')
    with pytest.raises(ValueError,match='Unsafe'):
        list(export.product_files('ensembles'))


def test_sunset_lookup_binary_is_validated_and_cname_is_preserved(tmp_path,monkeypatch):
    monkeypatch.setattr(export,'ROOT',tmp_path)
    folder=tmp_path/'generated/sunset';folder.mkdir(parents=True)
    for name in ('latest.json','lookup.json'):
        (folder/name).write_text('{}')
    (folder/'latest.png').write_bytes(b'fixture')
    with pytest.raises(FileNotFoundError,match='lookup.bin.gz'):
        list(export.product_files('sunset'))
    (tmp_path/'CNAME').write_text('chweather.org\n')
    assert tmp_path/'CNAME' in list(export.static_files())


def test_workflow_generates_every_packaged_product_before_publishing():
    workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/sunset.yml').read_text()
    products=re.search(r'product: \[([^\]]+)\]',workflow).group(1)
    assert {p.strip() for p in products.split(',')}==set(export.PRODUCTS)-{'models'}
    assert 'needs: [verify, generate]' in workflow
    assert 'fail-fast: false' in workflow
    assert '--check --product "$PRODUCT"' in workflow
    assert 'merge-multiple: true' in workflow
    assert 'timezone: America/New_York' in workflow
    assert 'timeout-minutes: 40' in workflow
    assert '--only-binary=:all:' in workflow
    assert 'sudo timeout 120 apt-get' in workflow
    models=(Path(__file__).resolve().parents[1]/'.github/workflows/models.yml').read_text()
    assert 'model: [gfs, hrrr, nam]' in models
    assert 'python -m models --model "$MODEL"' in models
    publish=(Path(__file__).resolve().parents[1]/'.github/workflows/publish.yml').read_text()
    assert 'workflows: [Daily weather and sunset outlooks, Scheduled weather models]' in publish
    assert 'scripts.collect_publication' in publish
