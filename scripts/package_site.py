"""Allowlisted static export; never publish Python, caches, or source documents."""
import argparse
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent.parent


def site_files():
    yield ROOT/'index.html'
    yield ROOT/'README.md'
    yield ROOT/'docs/SUNSET.md'
    yield ROOT/'docs/CHANGES-SUNSET.md'
    yield ROOT/'docs/OUTLOOKS.md'
    yield ROOT/'docs/CHANGES-OUTLOOKS.md'
    yield ROOT/'docs/LOCAL-FORECAST.md'
    yield ROOT/'docs/CHANGES-LOCAL-FORECAST.md'
    yield ROOT/'docs/MODELS.md'
    yield ROOT/'docs/CHANGES-MODELS.md'
    yield ROOT/'docs/AIRPORTS.md'
    yield ROOT/'docs/CHANGES-AIRPORTS.md'
    yield from sorted((ROOT/'portfolio').glob('*.html'))
    yield ROOT/'sunset/index.html'
    yield ROOT/'outlooks/index.html'
    yield ROOT/'models/index.html'
    yield from sorted(p for p in (ROOT/'assets').rglob('*') if p.is_file())
    yield ROOT/'output/pdf/christopher-horne-resume-placeholder.pdf'
    yield ROOT/'generated/sunset/latest.png'
    yield ROOT/'generated/sunset/latest.json'
    yield ROOT/'generated/sunset/lookup.json'
    yield ROOT/'generated/weather/latest.json'
    import json
    manifest=json.loads((ROOT/'generated/weather/latest.json').read_text(encoding='utf-8'))
    for product in manifest['products']:
        filename=product['image_filename']
        if Path(filename).name!=filename or not filename.endswith('.png'):
            raise ValueError('Invalid weather graphic filename')
        yield ROOT/'generated/weather'/filename
    yield ROOT/'generated/models/latest.json'
    models=json.loads((ROOT/'generated/models/latest.json').read_text(encoding='utf-8'))
    for model in models['models']:
        if model['status']!='available':continue
        for frame in model['frames']:
            names={image['image_filename'] for image in frame.get('images',{'precip':frame}).values()}
            if frame.get('readouts'):names.add(frame['readouts']['filename'])
            for filename in sorted(names):
                if Path(filename).name!=filename or Path(filename).suffix not in ('.png','.bin'):
                    raise ValueError('Invalid model asset filename')
                yield ROOT/'generated/models'/filename
    airport_root=ROOT/'generated/models/airports'
    yield airport_root/'latest.json'
    airport_manifest=json.loads((airport_root/'latest.json').read_text(encoding='utf-8'))
    yield airport_root/'catalog.json'
    for model in airport_manifest['models']:
        for chunk in model['chunks']:
            filename=chunk['filename']
            if Path(filename).name!=filename or not filename.endswith('.bin'):
                raise ValueError('Invalid airport asset filename')
            yield airport_root/filename


def package(output, zipped=False):
    output=Path(output).resolve()
    # Never delete the target: refuse to overwrite an existing unrelated tree.
    if output == ROOT or ROOT in output.parents and output.parts[-1] in ('assets','portfolio','sunset','generated'):
        raise ValueError('Unsafe export target')
    files=list(site_files())
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
    if zipped:
        output.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(output,'w',ZIP_DEFLATED) as archive:
            for path in files: archive.write(path,path.relative_to(ROOT).as_posix())
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
    args=parser.parse_args()
    package(args.zip_path or args.output_dir,bool(args.zip_path))
