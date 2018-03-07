#!/usr/bin/env python3

import gzip
import shutil
import time
from pathlib import Path


def compress(filename):
    with open(filename, 'rb') as fin:
        with gzip.open(filename + '.gz', 'wb') as fout:
            shutil.copyfileobj(fin, fout)


def main():
    while True:
        paths = [str(path) for path in Path('/orderbooks').glob('orderbook-*[!.gz]')]
        print(f'currently {len(paths)} order book logs')
        for path in paths:
            if time.strftime('%Y%m%d') not in path:
                print(f'compressing {path}')
                compress(path)
                # TODO: Send archive to S3; remove both from host
        time.sleep(60)


if __name__ == '__main__':
    main()
