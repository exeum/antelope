#!/usr/bin/env python3

import argparse
import bz2
import logging
import shutil
import time
from pathlib import Path

import boto3

INTERVAL = 60
EXPIRY = 300


def compress(path):
    with open(path, "rb") as fin:
        with bz2.open(str(path) + ".bz2", "wb") as fout:
            shutil.copyfileobj(fin, fout)


def upload(path, s3, bucket):
    logging.info(f"uploading {path.name} to {bucket}")
    s3.upload_file(str(path), bucket, path.name)
    logging.info(f"verifying {path.name} got uploaded")
    s3.head_object(Bucket=bucket, Key=path.name)


def remove(path):
    logging.info(f"removing {path.name}")
    path.unlink()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="us-east-2")
    parser.add_argument("--bucket", default="exeum-antelope")
    return parser.parse_args()


def main():
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.INFO)
    args = parse_args()
    s3 = boto3.client("s3", region_name=args.region)
    while True:
        data_path = Path("/data")
        for path in data_path.glob("*"):
            if path.suffix == ".bz2":
                continue
            time_inactive = time.time() - path.stat().st_mtime
            logging.info(f"{path.name} inactive for {int(time_inactive)} seconds")
            if time_inactive >= EXPIRY:
                logging.info(f"compressing {path.name}")
                compress(path)
        for path in data_path.glob("*.bz2"):
            upload(path, s3, args.bucket)
            remove(path)
            remove(path.parent.joinpath(path.stem))
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
