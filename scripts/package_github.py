"""Create a correctly structured source ZIP for a GitHub repository upload."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from scripts.package_site import ROOT,site_files


def package():
    files=set(site_files())
    files.update(ROOT/path for path in ['.gitignore','.github/workflows/sunset.yml',
                  'requirements-sunset.txt','requirements-sunset-dev.txt'])
    for directory in ['sunset','weather','scripts','tests']:
        files.update((ROOT/directory).glob('*.py'))
    files.add(ROOT/'sunset/cities.json')
    out=ROOT/'output/ch-weather-github-ready.zip'
    with ZipFile(out,'w',ZIP_DEFLATED) as archive:
        for path in sorted(files): archive.write(path,path.relative_to(ROOT).as_posix())
    print(f'Packaged {len(files)} GitHub source/website files: {out}')


if __name__=='__main__':package()
