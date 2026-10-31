"""Publish validated product artifacts independently, retaining older successful data."""
from datetime import datetime,timezone
import hashlib
import json
import os
import shutil
from pathlib import Path,PurePosixPath
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlencode,urlparse
from urllib.request import Request,urlopen,build_opener,HTTPRedirectHandler
from zipfile import ZipFile
from scripts.package_site import product_files
from scripts.merge_models import check_part,merge

ROOT=Path(__file__).resolve().parent.parent
FAMILIES={'outlooks':('sunset.yml','outlooks-bundle',{'sunset','weather','tropical','centers','enso','analysis','ensembles'}),
          'models':('models.yml','models-bundle',{'models'})}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


def headers(token):
    return {'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'User-Agent':'CHWeather-Publication'}


def api(path,token):
    with urlopen(Request('https://api.github.com/'+path,headers=headers(token)),timeout=45) as response:
        return json.load(response)


def artifact_candidates(repository,name,token):
    query=urlencode({'name':name,'per_page':30})
    artifacts=api(f'repos/{repository}/actions/artifacts?{query}',token)['artifacts']
    return sorted((a for a in artifacts if a['name']==name and not a['expired'] and (a.get('workflow_run') or {}).get('head_branch')=='main'),key=lambda a:a['created_at'],reverse=True)


def extract(archive,destination,products):
    destination=Path(destination).resolve()
    with ZipFile(archive) as bundle:
        items=bundle.infolist()
        if len(items)>20000 or sum(i.file_size for i in items)>2_000_000_000:raise ValueError('Publication artifact exceeds supported size')
        for item in items:
            name=PurePosixPath(item.filename)
            if item.is_dir() and name.parts==('generated',):continue
            if (name.is_absolute() or '..' in name.parts or '\\' in item.filename or ':' in item.filename
                or len(name.parts)<2 or name.parts[0]!='generated' or name.parts[1] not in products
                or (item.external_attr>>16)&0o170000==0o120000):raise ValueError(f'Unsafe publication artifact entry: {item.filename}')
            if item.is_dir():continue
            target=destination.joinpath(*name.parts)
            target.parent.mkdir(parents=True,exist_ok=True)
            with bundle.open(item) as source,target.open('wb') as output:
                while chunk:=source.read(1024*1024):output.write(chunk)


def download_artifact(repository,artifact,token,target):
    url=f'https://api.github.com/repos/{repository}/actions/artifacts/{artifact["id"]}/zip'
    try:
        response=build_opener(NoRedirect).open(Request(url,headers=headers(token)),timeout=45)
    except HTTPError as exc:
        if exc.code not in (301,302,303,307,308):raise
        signed=exc.headers['Location']
        if urlparse(signed).scheme!='https':raise ValueError('Artifact download must use HTTPS')
        # GitHub redirects to a signed storage URL. Never forward the repository token.
        response=urlopen(Request(signed,headers={'User-Agent':'CHWeather-Publication'}),timeout=90)
    size=0;digest=hashlib.sha256()
    with response,target.open('wb') as output:
        while chunk:=response.read(1024*1024):
            size+=len(chunk)
            if size>2_000_000_000:raise ValueError('Artifact download exceeds supported size')
            output.write(chunk);digest.update(chunk)
    expected=artifact.get('digest')
    if expected and expected!='sha256:'+digest.hexdigest():raise ValueError('Publication artifact digest mismatch')


def unavailable_models(root):
    folder=Path(root)/'generated/models';(folder/'airports').mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    manifest={'schema_version':2,'generated_at_utc':now,'models':[],'status':'unavailable',
              'message':'No completed model bundle is available yet. Outlook updates are published independently.'}
    (folder/'latest.json').write_text(json.dumps(manifest)+'\n',encoding='utf-8')
    (folder/'airports/catalog.json').write_text('[]\n',encoding='utf-8')
    (folder/'airports/latest.json').write_text(json.dumps({'schema_version':1,'generated_at_utc':now,'models':[],
        'catalog_filename':'catalog.json','catalog_count':0,'status':'unavailable'})+'\n',encoding='utf-8')


def unavailable_product(root,product):
    folder=Path(root)/'generated'/product;folder.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    metadata=dict(schema_version=1,generated_at_utc=now,status='unavailable',products=[],models=[],basins=[],
        message='No validated successful data is available for this product yet. Other products update independently.')
    (folder/'latest.json').write_text(json.dumps(metadata)+'\n',encoding='utf-8')


def restore_product(repository,product,token,temporary):
    candidates=artifact_candidates(repository,'forecast-'+product,token)
    weather=None;selected={};expected=set()
    for index,artifact in enumerate(candidates[:6]):
        destination=temporary/f'{product}-{index}';archive=temporary/f'{product}-{index}.zip'
        try:
            download_artifact(repository,artifact,token,archive);extract(archive,destination,{product})
            paths=list(product_files(product,destination))
            metadata=json.loads((destination/'generated'/product/'latest.json').read_text(encoding='utf-8'))
            if metadata.get('status')=='unavailable':continue
            if product!='weather':
                for path in paths:
                    target=ROOT/path.relative_to(destination);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
                print(f'Restored {product}: validated artifact {artifact["id"]}');return True
            if weather is None:
                weather=metadata
                expected={'spc-day1','spc-day2','spc-day3','weather-national','weather-nc','rain-national','rain-nc'}
                if metadata.get('foliage_status')!='out_of_season':expected.update({'foliage-national','foliage-nc'})
            for item in metadata.get('products',[]):
                if item['id'] not in expected or item['id'] in selected:continue
                value=dict(item)
                if index:value['retained_from_previous_publication']=True
                selected[item['id']]=value
                source=destination/'generated/weather'/item['image_filename'];target=ROOT/'generated/weather'/item['image_filename']
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
            if expected<=selected.keys():break
        except Exception as error:print(f'{product} artifact {artifact["id"]} could not be used: {error}')
        finally:archive.unlink(missing_ok=True)
    if product=='weather' and selected:
        folder=ROOT/'generated/weather';folder.mkdir(parents=True,exist_ok=True)
        weather=dict(weather,products=list(selected.values()),retained_products=[k for k,v in selected.items() if v.get('retained_from_previous_publication')])
        (folder/'latest.json').write_text(json.dumps(weather,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        print(f'Restored weather: {len(selected)} products, {len(weather["retained_products"])} retained from earlier updates');return True
    return False


def restore_model(repository,model,token,temporary):
    for index,artifact in enumerate(artifact_candidates(repository,'model-'+model,token)[:3]):
        destination=temporary/f'{model}-{index}';archive=temporary/f'{model}-{index}.zip'
        try:
            download_artifact(repository,artifact,token,archive);extract(archive,destination,{'models'})
            source=destination/'generated/models';_,paths=check_part(source,model)
            for path in paths:
                target=temporary/'parts'/f'model-{model}'/'generated/models'/path.relative_to(source)
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
            print(f'Restored {model}: validated artifact {artifact["id"]}');return True
        except Exception as error:print(f'{model} artifact {artifact["id"]} could not be used: {error}')
        finally:archive.unlink(missing_ok=True)
    return False


def main():
    token=os.environ.get('GH_TOKEN');repository=os.environ.get('GITHUB_REPOSITORY')
    if not token or not repository:raise RuntimeError('GH_TOKEN and GITHUB_REPOSITORY are required; Actions supplies both automatically.')
    successes=0
    with tempfile.TemporaryDirectory() as directory:
        temporary=Path(directory)
        for product in sorted(FAMILIES['outlooks'][2]):
            try:available=restore_product(repository,product,token,temporary)
            except Exception as error:print(f'{product} update unavailable: {error}');available=False
            if available:successes+=1
            else:unavailable_product(ROOT,product)
        models=[]
        for model in ('gfs','hrrr','nam'):
            try:
                if restore_model(repository,model,token,temporary):models.append(model)
            except Exception as error:print(f'{model} update unavailable: {error}')
        if models:
            merge(temporary/'parts',ROOT/'generated/models',allow_missing=True);successes+=len(models)
        else:unavailable_models(ROOT)
    if not successes:raise RuntimeError('No validated product artifacts were available. Existing published website is retained.')
    print(f'Publication assembled from {successes} independent successful product/model artifacts.')
    return 0


if __name__=='__main__':raise SystemExit(main())
