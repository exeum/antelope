#!/usr/bin/env python3

import argparse
import gzip
import logging
import shutil
import time
from pathlib import Path

import boto3

INTERVAL = 60
EXPIRY = 600


def compress(path):
    with open(path, 'rb') as fin:
        with gzip.open(str(path) + '.gz', 'wb') as fout:
            shutil.copyfileobj(fin, fout)


def upload(path, s3, bucket):
    logging.info(f'uploading {path.name} to {bucket}')
    s3.upload_file(str(path), bucket, path.name)
    logging.info(f'verifying {path.name} got uploaded')
    s3.head_object(Bucket=bucket, Key=path.name)


def remove(path):
    logging.info(f'removing {path.name}')
    path.unlink()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', default='us-east-2')
    parser.add_argument('--bucket', default='exeum-antelope')
    return parser.parse_args()


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    s3 = boto3.client('s3', region_name=args.region)
    while True:
        data_path = Path('/data')
        for path in data_path.glob('*[!.gz]'):
            time_inactive = time.time() - path.stat().st_mtime
            if time_inactive >= EXPIRY:
                logging.info(f'{path.name} inactive for {time_inactive} seconds; compressing')
                compress(path)
        for path in data_path.glob('*.gz'):
            upload(path, s3, args.bucket)
            remove(path)
            remove(path.parent.joinpath(path.stem))
        logging.info(f'sleeping for {INTERVAL} seconds')
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
