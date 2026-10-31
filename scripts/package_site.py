"""Validate and export public website files and manifest-referenced weather assets."""
import argparse
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent.parent
PRODUCTS=('sunset','weather','tropical','centers','enso','analysis','ensembles','models')
PAGES=('portfolio','sunset','outlooks','models','tropical','satellite','alerts','analysis','mos','ensembles','enso','radar')


def static_files():
    yield ROOT/'index.html'
    yield ROOT/'README.md'
    for directory in PAGES:
        yield from sorted((ROOT/directory).glob('*.html'))
    yield from sorted((ROOT/'docs').glob('*.md'))
    yield from sorted(p for p in (ROOT/'assets').rglob('*') if p.is_file())
    yield ROOT/'output/pdf/christopher-horne-resume-placeholder.pdf'
    if (ROOT/'CNAME').is_file():
        yield ROOT/'CNAME'


def references(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key.endswith('filename') and isinstance(item,str):
                if (not item or '/' in item or '\\' in item or Path(item).name!=item
                        or item in ('.','..') or not item.endswith(('.png','.json','.bin','.bin.gz','.webp'))):
                    raise ValueError(f'Unsafe generated asset filename: {item!r}')
                yield item
            else:
                yield from references(item)
    elif isinstance(value,list):
        for item in value:
            yield from references(item)


def product_files(product):
    if product not in PRODUCTS:
        raise ValueError(f'Unknown product: {product}')
    folder=ROOT/'generated'/product
    required=[folder/'latest.json']
    if product=='sunset':
        required.extend(folder/name for name in ('latest.png','lookup.json','lookup.bin.gz'))
    if product=='models':
        required.extend(folder/'airports'/name for name in ('latest.json','catalog.json'))
    missing=[p.relative_to(ROOT).as_posix() for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError(f'{product}: missing {", ".join(missing)}. Run python -m {product} before packaging. Replace .github/workflows/sunset.yml with the matching current workflow.')
    seen=set()
    pending=list(required)
    while pending:
        path=pending.pop(0)
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file() or path.stat().st_size==0:
            raise FileNotFoundError(f'{product}: missing or empty referenced asset {path.relative_to(ROOT)}. Regenerate with python -m {product}.')
        yield path
        if path.suffix=='.json':
            try:
                manifest=json.loads(path.read_text(encoding='utf-8'))
            except (ValueError,UnicodeError) as exc:
                raise ValueError(f'{product}: invalid JSON in {path.relative_to(ROOT)}') from exc
            pending.extend(path.parent/name for name in references(manifest))


def site_files(include_generated=True):
    yield from static_files()
    if include_generated:
        missing=[p for p in PRODUCTS if not (ROOT/'generated'/p/'latest.json').is_file()]
        if missing:
            commands='; '.join(f'python -m {p}' for p in missing)
            raise FileNotFoundError(f'Missing generated products: {", ".join(missing)}. The website cannot be published with broken forecast links. Required commands: {commands}. Update .github/workflows/sunset.yml together with the source files.')
        for product in PRODUCTS:
            yield from product_files(product)


def checked_files(product=None):
    files=list(dict.fromkeys(product_files(product) if product else site_files()))
    missing=[p.relative_to(ROOT).as_posix() for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError('Missing website files: '+', '.join(missing))
    return files


def package(output,zipped=False):
    output=Path(output).resolve()
    if output==ROOT or ROOT in output.parents and output.name in ('assets','portfolio','sunset','generated'):
        raise ValueError('Unsafe export target')
    files=checked_files()
    if zipped:
        output.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(output,'w',ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path,path.relative_to(ROOT).as_posix())
    else:
        if output.exists():
            raise FileExistsError(f'Choose a fresh export directory: {output}')
        output.mkdir(parents=True)
        for path in files:
            target=output/path.relative_to(ROOT)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,target)
    print(f'Packaged {len(files)} static files: {output}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',default='_site')
    parser.add_argument('--zip',dest='zip_path')
    parser.add_argument('--check',action='store_true',help='Validate without copying or packaging')
    parser.add_argument('--product',choices=PRODUCTS,help='Validate one generator output (requires --check)')
    args=parser.parse_args()
    if args.product and not args.check:
        parser.error('--product requires --check')
    if args.check:
        print(f'Validated {len(checked_files(args.product))} files: {args.product or "complete website"}')
    else:
        package(args.zip_path or args.output_dir,bool(args.zip_path))
