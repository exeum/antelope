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
EXPIRY = 60 * 60


def compress(filename_in, filename_out):
    logging.info(f'compressing {filename_in}')
    with open(filename_in, 'rb') as fin:
        with gzip.open(filename_out, 'wb') as fout:
            shutil.copyfileobj(fin, fout)


def file_age(filename):
    return time.time() - os.path.getmtime(filename)


def remove(filename):
    logging.info(f'removing {filename}')
    os.remove(filename)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', default='/data')
    parser.add_argument('--region', default='us-east-1')
    parser.add_argument('--bucket', default='antelope')
    return parser.parse_args()


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    #s3 = boto3.client('s3', region_name=args.region)
    while True:
        paths = [str(path) for path in Path(args.dir).glob('*[!.gz]')]
        logging.info(f'currently {len(paths)} order book logs')
        for path in paths:
            if file_age(path) > EXPIRY:
                path_gz = path + '.gz'
                compress(path, path_gz)
                #s3.upload_file(path_gz, args.bucket, path_gz)
                #remove(path_gz)
                remove(path)
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
