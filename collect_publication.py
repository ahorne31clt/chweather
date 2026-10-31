"""Combine the newest successful independent outlook and model artifacts for Pages."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlencode,urlparse
from urllib.request import Request,urlopen,build_opener,HTTPRedirectHandler
from zipfile import ZipFile

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


def latest_artifact(repository,workflow,name,token):
    query=urlencode({'status':'success','branch':'main','per_page':10})
    try:runs=api(f'repos/{repository}/actions/workflows/{workflow}/runs?{query}',token)['workflow_runs']
    except HTTPError as exc:
        if exc.code==404:return None
        raise
    for run in runs:
        if run.get('head_branch')!='main' or run.get('event')=='pull_request':continue
        artifacts=api(f'repos/{repository}/actions/runs/{run["id"]}/artifacts?per_page=100',token)['artifacts']
        for artifact in artifacts:
            if artifact['name']==name and not artifact['expired']:return artifact
    return None


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


def main():
    token=os.environ.get('GH_TOKEN');repository=os.environ.get('GITHUB_REPOSITORY')
    if not token or not repository:raise RuntimeError('GH_TOKEN and GITHUB_REPOSITORY are required; the publication workflow supplies both automatically.')
    found={family:latest_artifact(repository,workflow,name,token) for family,(workflow,name,_) in FAMILIES.items()}
    if not found['outlooks']:raise RuntimeError('Waiting for the first successful outlooks-bundle. Run Daily weather and sunset outlooks once; its completion automatically retries publication.')
    with tempfile.TemporaryDirectory() as temporary:
        temporary=Path(temporary)
        for family,artifact in found.items():
            if artifact is None:continue
            target=temporary/(family+'.zip');download_artifact(repository,artifact,token,target)
            extract(target,ROOT,FAMILIES[family][2]);print(f'Collected {family}: artifact {artifact["id"]}, created {artifact["created_at"]}')
    if found['models'] is None:
        unavailable_models(ROOT);print('No model bundle yet: explicit unavailable status; outlooks can still publish.')
    return 0


if __name__=='__main__':raise SystemExit(main())
