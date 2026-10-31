import io
import json
from pathlib import Path
from zipfile import ZipFile
import pytest
from scripts import merge_models as merge
from scripts import collect_publication as collect
from scripts import package_site as export


def part(root,model):
    folder=root/f'model-{model}'/'generated/models';folder.mkdir(parents=True)
    end={'gfs':384,'hrrr':48,'nam':84}[model];step=1 if model=='hrrr' else 3
    item={'id':model,'status':'available','model_run':'2026-10-31T00:00:00Z','extended_run':model=='hrrr',
          'frames':[{'hour':h,'image_filename':f'{model}-{h}.png'} for h in range(0,end+1,step)]}
    (folder/'latest.json').write_text(json.dumps({'schema_version':2,'models':[item]}))
    for frame in item['frames']:(folder/frame['image_filename']).write_bytes(b'image')
    if model!='nam':
        (folder/'airports').mkdir();(folder/'airports/catalog.json').write_text('[]')
        (folder/f'airports/{model}.bin').write_bytes(b'airport')
        a={'id':model,'model_run':item['model_run'],'chunks':[{'filename':model+'.bin'}]}
        (folder/'airports/latest.json').write_text(json.dumps({'models':[a],'catalog_filename':'catalog.json','catalog_sha256':'matching-fixture-catalog'}))
    return folder


def test_merge_keeps_all_models_and_both_matching_airport_runs(tmp_path):
    for model in ('gfs','hrrr','nam'):part(tmp_path/'parts',model)
    out=tmp_path/'merged';out.mkdir();(out/'gfs-0.png').write_bytes(b'old checkout image')
    result=merge.merge(tmp_path/'parts',out)
    assert [m['id'] for m in result['models']]==['gfs','hrrr','nam']
    assert [len(m['frames']) for m in result['models']]==[129,49,29]
    assert (out/'gfs-0.png').read_bytes()==b'image'
    airport=json.loads((out/'airports/latest.json').read_text())
    assert [m['id'] for m in airport['models']]==['gfs','hrrr']


def test_partial_model_cannot_masquerade_as_full_run(tmp_path):
    folder=part(tmp_path,'gfs');data=json.loads((folder/'latest.json').read_text());data['models'][0]['frames'].pop()
    (folder/'latest.json').write_text(json.dumps(data))
    with pytest.raises(ValueError,match='complete forecast-hour range'):merge.check_part(folder,'gfs')


def test_part_artifact_excludes_other_models_and_orphaned_files(tmp_path):
    folder=part(tmp_path/'parts','nam');(folder/'old-gfs.png').write_bytes(b'orphan')
    paths=merge.check_part(folder,'nam')[1]
    merge.stage(paths,folder,tmp_path/'artifact')
    assert (tmp_path/'artifact/generated/models/latest.json').is_file()
    assert not (tmp_path/'artifact/generated/models/old-gfs.png').exists()


def test_unavailable_models_do_not_block_outlook_packaging(tmp_path,monkeypatch):
    monkeypatch.setattr(export,'ROOT',tmp_path)
    collect.unavailable_models(tmp_path)
    paths=list(export.product_files('models'))
    assert len(paths)==1
    assert json.loads((tmp_path/'generated/models/latest.json').read_text())['models']==[]


def test_artifacts_keep_family_boundaries_and_reject_path_traversal(tmp_path):
    archive=io.BytesIO()
    with ZipFile(archive,'w') as z:z.writestr('generated/sunset/latest.json','{}')
    archive.seek(0);collect.extract(archive,tmp_path,{'sunset'})
    assert (tmp_path/'generated/sunset/latest.json').is_file()
    for name in ('../private.txt','generated/models/latest.json','generated/sunset/../../private.txt'):
        archive=io.BytesIO()
        with ZipFile(archive,'w') as z:z.writestr(name,'bad')
        archive.seek(0)
        with pytest.raises(ValueError,match='Unsafe'):collect.extract(archive,tmp_path,{'sunset'})


def test_independent_artifacts_keep_valid_jobs_even_if_other_jobs_failed(monkeypatch):
    def api(path,token):
        return {'artifacts':[
            {'name':'model-gfs','expired':False,'id':99,'created_at':'2026-10-31T00:00:00Z','workflow_run':{'head_branch':'main'}},
            {'name':'model-gfs','expired':True,'id':100,'created_at':'2026-10-31T01:00:00Z','workflow_run':{'head_branch':'main'}}]}
    monkeypatch.setattr(collect,'api',api)
    assert collect.artifact_candidates('owner/repo','model-gfs','fake')[0]['id']==99


def test_nam_only_still_publishes_when_gfs_and_hrrr_have_no_successful_run(tmp_path):
    part(tmp_path/'parts','nam')
    result=merge.merge(tmp_path/'parts',tmp_path/'out',allow_missing=True)
    assert [m['id'] for m in result['models'] if m['status']=='available']==['nam']
    assert json.loads((tmp_path/'out/airports/latest.json').read_text())['models']==[]


def test_publisher_keeps_other_products_when_one_product_raises(tmp_path,monkeypatch):
    monkeypatch.setattr(collect,'ROOT',tmp_path)
    monkeypatch.setenv('GH_TOKEN','fixture');monkeypatch.setenv('GITHUB_REPOSITORY','fixture/repo')
    def restore(repository,product,token,temporary):
        if product=='weather':raise ValueError('failed weather fixture')
        if product!='centers':return False
        folder=tmp_path/'generated/centers';folder.mkdir(parents=True)
        (folder/'latest.json').write_text('{"schema_version":1,"products":[]}')
        return True
    monkeypatch.setattr(collect,'restore_product',restore)
    monkeypatch.setattr(collect,'restore_model',lambda *args:False)
    assert collect.main()==0
    assert json.loads((tmp_path/'generated/weather/latest.json').read_text())['status']=='unavailable'
    assert json.loads((tmp_path/'generated/centers/latest.json').read_text()).get('status')!='unavailable'
    for product in export.PRODUCTS:list(export.product_files(product,tmp_path))


def test_partial_weather_restores_old_missing_maps_without_overwriting_new_spc(tmp_path,monkeypatch):
    monkeypatch.setattr(collect,'ROOT',tmp_path/'site')
    monkeypatch.setattr(collect,'artifact_candidates',lambda *args:[{'id':2},{'id':1}])
    old_ids=['spc-day1','spc-day2','spc-day3','weather-national','weather-nc','rain-national','rain-nc']
    def download(repository,artifact,token,target):
        ids=old_ids[:3] if artifact['id']==2 else old_ids
        products=[dict(id=id,image_filename=id+'.png',generated_at_utc='new' if artifact['id']==2 else 'old') for id in ids]
        with ZipFile(target,'w') as z:
            z.writestr('generated/weather/latest.json',json.dumps({'products':products,'foliage_status':'out_of_season'}))
            for id in ids:z.writestr('generated/weather/'+id+'.png',str(artifact['id']))
    monkeypatch.setattr(collect,'download_artifact',download)
    temp=tmp_path/'temporary';temp.mkdir()
    assert collect.restore_product('repo','weather','fixture',temp)
    folder=tmp_path/'site/generated/weather';manifest=json.loads((folder/'latest.json').read_text())
    assert len(manifest['products'])==7
    assert len(manifest['retained_products'])==4
    assert (folder/'spc-day1.png').read_text()=='2'
    assert (folder/'rain-nc.png').read_text()=='1'
