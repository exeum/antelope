#!/usr/bin/env python3

import gzip
import shutil
from pathlib import Path


def compress(filename):
    with open(filename, 'rb') as fin:
        with gzip.open(filename + '.gz', 'wb') as fout:
            shutil.copyfileobj(fin, fout)


def main():
    for path in Path('data').glob('orderbook-*'):Aa
        if not path.endswith('.gz') and time.strftime('%Y%m%d') not in path:
            print(f'compressing {path}')
            compress(path)


if __name__ == '__main__':
    main()
