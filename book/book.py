#!/usr/bin/env python3

import argparse
import json
import logging
import time
import uuid
from random import random

import influxdb
import requests
from retrying import retry

TIMEOUT = 5
RETRIES = 3


def write_point(db, measurement, exchange, symbol, scraper_id, size):
    point = {
        'measurement': measurement,
        'tags': {
            'exchange': exchange,
            'symbol': symbol,
            'scraper_id': scraper_id
        },
        'time': time.time(),
        'fields': {
            'size': float(size),
        }
    }
    db.write_points([point])


@retry(stop_max_attempt_number=RETRIES)
def get(url):
    return requests.get(url, timeout=TIMEOUT).text


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('exchange')
    parser.add_argument('symbol')
    parser.add_argument('url')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='antelope')
    parser.add_argument('--interval', type=float, default=1)
    return parser.parse_args()


def wrap_data(data):
    return json.dumps({
        'timestamp': time.time(),
        'data': json.loads(data)
    }, separators=(',', ':'))


def append_line(filename, line):
    with open(filename, 'at') as f:
        f.write(line + '\n')


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    scraper_id = uuid.uuid4().hex
    kind = 'book'
    filename = f'/data/{kind}-{args.exchange}-{args.symbol}-{scraper_id}'

    while True:
        data = get(args.url)

        size = len(data)
        logging.info(f'got {size} bytes')
        write_point(db, kind, args.exchange, args.symbol, scraper_id, size)
        append_line(filename, wrap_data(data))

        random_delay = args.interval * random()
        time.sleep(args.interval + random_delay)


if __name__ == '__main__':
    main()
