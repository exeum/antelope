#!/usr/bin/env python3

import argparse
import gzip
import os
import shutil
import time
from pathlib import Path

import boto3


def compress(filename_in, filename_out):
    with open(filename_in, 'rb') as fin:
        with gzip.open(filename_out, 'wb') as fout:
            shutil.copyfileobj(fin, fout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', default='us-east-1')
    parser.add_argument('--bucket', default='antelope')
    args = parser.parse_args()
    s3 = boto3.client('s3', region_name=args.region)
    while True:
        paths = [str(path) for path in Path('/orderbooks').glob('orderbook-*[!.gz]')]
        print(f'currently {len(paths)} order book logs')
        for path in paths:
            if time.strftime('%Y%m%d') not in path:
                path_gz = path + '.gz'
                print(f'compressing {path} as {path_gz}')
                compress(path, path_gz)
                s3.upload_file(path_gz, args.bucket, path_gz)
                print(f'removing {path}')
                os.remove(path)
                print(f'removing {path_gz}')
                os.remove(path_gz)
        time.sleep(60)


if __name__ == '__main__':
    main()
