"""Run one independently scheduled forecast family without interactive input."""
import argparse,subprocess,sys
from scripts.package_site import PRODUCTS


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('product',choices=PRODUCTS);args=parser.parse_args()
    command=[sys.executable,'-m','specialty','--product',args.product.removeprefix('specialty-')] if args.product.startswith('specialty-') else [sys.executable,'-m',args.product]
    return subprocess.call(command)


if __name__=='__main__':raise SystemExit(main())
