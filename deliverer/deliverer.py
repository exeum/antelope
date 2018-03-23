#!/usr/bin/env python3

import argparse
import gzip
import logging
import os
import shutil
import time
from pathlib import Path

import boto3

INTERVAL = 60
EXPIRY = 600


def compress(filename):
    logging.info(f'compressing {filename}')
    with open(filename, 'rb') as fin:
        with gzip.open(filename + '.gz', 'wb') as fout:
            shutil.copyfileobj(fin, fout)


def remove(path):
    logging.info(f'removing {path.name}')
    path.unlink()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', default='/data')
    parser.add_argument('--region', default='us-east-1')
    parser.add_argument('--bucket', default='antelope')
    return parser.parse_args()


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    s3 = boto3.client('s3', region_name=args.region)
    while True:
        dir_path = Path(args.dir)
        for path in dir_path.glob('*[!.gz]'):
            if time.time() - path.stat().st_mtime >= EXPIRY:
                compress(str(path))
        for path in dir_path.glob('*.gz'):
            s3.upload_file(str(path), args.bucket, str(path.name))
            remove(path)
            remove(os.path.splitext(path)[0])
            pass
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
