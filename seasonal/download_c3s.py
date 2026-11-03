"""Optional bounded C3S staging download; never silently adds unverified models.

Use the dataset portal's exact JSON request, after accepting its terms.
Credentials come only from CDSAPI_KEY. This command stages data for evaluation;
it does not claim that unsupported units or unmatched hindcasts are blend-ready.
"""
import argparse
import json
import os
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    key=os.environ.get('CDSAPI_KEY')
    if not key:raise ValueError('Set CDSAPI_KEY in the environment; never put it in request JSON')
    request=json.loads(args.request.read_text(encoding='utf-8'))
    forbidden={'key','token','password','url'}
    if forbidden.intersection(request):raise ValueError('Credentials are forbidden in the request file')
    if len(request.get('year',[]))>30:raise ValueError('Split the archive into requests of at most 30 years')
    if 'area' not in request:raise ValueError('Specify a bounded area, for example [51,-127,23,-65]')
    import cdsapi
    client=cdsapi.Client(url='https://cds.climate.copernicus.eu/api',key=key,quiet=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    partial=args.output.with_suffix(args.output.suffix+'.part')
    try:
        client.retrieve('seasonal-monthly-single-levels',request,str(partial))
        if not partial.is_file() or not partial.stat().st_size:raise ValueError('Empty C3S response')
        partial.replace(args.output)
    finally:
        partial.unlink(missing_ok=True)


if __name__=='__main__':main()
