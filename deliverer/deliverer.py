#!/usr/bin/env python3

import gzip
import logging
import shutil
import time
from pathlib import Path


def compress(filename):
    with open(filename, 'rb') as fin:
        with gzip.open(filename + '.gz', 'wb') as fout:
            shutil.copyfileobj(fin, fout)


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    while True:
        for path in Path('/orderbooks').glob('*'):
            path = str(path)
            if not path.endswith('.gz') and time.strftime('%Y%m%d') not in path:
                logging.info(f'compressing {path}')
                compress(path)
        time.sleep(60)


if __name__ == '__main__':
    main()
