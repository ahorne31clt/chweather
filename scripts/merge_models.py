"""Validate and combine independently generated GFS, HRRR and NAM bundles."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
from scripts.package_site import references


def tree_files(manifest):
    pending=[manifest];seen=set()
    while pending:
        path=pending.pop(0)
        if path in seen:continue
        seen.add(path)
        if not path.is_file() or path.stat().st_size==0:raise ValueError(f'Missing model asset: {path}')
        yield path
        if path.suffix=='.json':
            data=json.loads(path.read_text(encoding='utf-8'))
            pending.extend(path.parent/name for name in references(data))


def check_part(folder,model):
    folder=Path(folder)
    manifest=json.loads((folder/'latest.json').read_text(encoding='utf-8'))
    if len(manifest['models'])!=1:raise ValueError('Each model job must publish exactly one model')
    item=manifest['models'][0]
    if item['id']!=model or item['status']!='available' or not item.get('frames'):raise ValueError(f'Incomplete {model} model job')
    if not isinstance(item.get('model_run'),str):raise ValueError('Missing model run')
    hours=[frame['hour'] for frame in item['frames']]
    end={'gfs':384,'hrrr':48,'nam':84}[model]
    if model=='hrrr' and not item.get('extended_run'):end=18
    step=1 if model=='hrrr' else 3
    if hours!=list(range(0,end+1,step)):raise ValueError(f'{model} job must retain its complete forecast-hour range')
    paths=list(tree_files(folder/'latest.json'))
    if model!='nam':
        airport=json.loads((folder/'airports/latest.json').read_text(encoding='utf-8'))
        if len(airport['models'])!=1 or airport['models'][0]['id']!=model or airport['models'][0]['model_run']!=item['model_run']:raise ValueError('Airport and map runs differ')
        paths.extend(tree_files(folder/'airports/latest.json'))
    return manifest,list(dict.fromkeys(paths))


def merge(parts,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    manifests=[];airports=[];catalog_hash=None;copied=set()
    for model in ('gfs','hrrr','nam'):
        folder=Path(parts)/f'model-{model}'/'generated/models'
        manifest,paths=check_part(folder,model);manifests.append(manifest)
        for path in paths:
            relative=path.relative_to(folder)
            if relative.as_posix() in ('latest.json','airports/latest.json'):continue
            target=output/relative;target.parent.mkdir(parents=True,exist_ok=True)
            if relative in copied and target.read_bytes()!=path.read_bytes():raise ValueError(f'Model jobs produced conflicting shared asset: {relative}')
            shutil.copy2(path,target)
            copied.add(relative)
        if model!='nam':
            a=json.loads((folder/'airports/latest.json').read_text(encoding='utf-8'))
            if catalog_hash is not None and catalog_hash!=a['catalog_sha256']:raise ValueError('Airport catalogs differ between model jobs; rerun to keep airport indices consistent')
            catalog_hash=a['catalog_sha256'];airports.append(a)
    now=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    combined=dict(manifests[0],models=[m['models'][0] for m in manifests],generated_at_utc=now)
    airport=dict(airports[0],models=[a['models'][0] for a in airports],generated_at_utc=now)
    (output/'airports/latest.json').write_text(json.dumps(airport,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (output/'latest.json').write_text(json.dumps(combined,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return combined


def stage(paths,folder,destination):
    folder=Path(folder)
    for path in paths:
        target=Path(destination)/'generated/models'/path.relative_to(folder)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parts',default='.model-parts')
    parser.add_argument('--output',default='generated/models')
    parser.add_argument('--check-part')
    parser.add_argument('--model',choices=['gfs','hrrr','nam'])
    parser.add_argument('--stage',help='Copy only validated referenced assets to this artifact root')
    args=parser.parse_args()
    if args.check_part:
        if not args.model:parser.error('--check-part requires --model')
        paths=check_part(args.check_part,args.model)[1]
        if args.stage:stage(paths,args.check_part,args.stage)
        print(f'Validated {len(paths)} {args.model} model assets')
    else:
        merge(args.parts,args.output)
        if args.stage:stage(list(tree_files(Path(args.output)/'latest.json'))+list(tree_files(Path(args.output)/'airports/latest.json')),args.output,args.stage)
