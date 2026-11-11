"""Run one independently scheduled forecast family without interactive input."""
import argparse,subprocess,sys
from scripts.package_site import PRODUCTS


def outlook_products(schedule=''):
    if schedule == '0 16 * * *':
        return ['sunset']
    return [product for product in PRODUCTS if product not in ('models', 'seasonal')
            and (product != 'sunset' or schedule in ('', '0 8 * * *'))]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('product',choices=PRODUCTS);args=parser.parse_args()
    command=[sys.executable,'-m','specialty','--product',args.product.removeprefix('specialty-')] if args.product.startswith('specialty-') else [sys.executable,'-m',args.product]
    return subprocess.call(command)


if __name__=='__main__':raise SystemExit(main())
