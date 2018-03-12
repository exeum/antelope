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


def write_point(db, exchange, symbol, scraper_id, size, latency):
    point = {
        'measurement': 'book',
        'tags': {
            'exchange': exchange,
            'symbol': symbol,
            'scraper_id': scraper_id
        },
        'time': time.time(),
        'fields': {
            'size': float(size),
            'latency': float(latency)
        }
    }
    db.write_points([point])


@retry(stop_max_attempt_number=RETRIES)
def get(url):
    res = requests.get(url, timeout=TIMEOUT)
    return res.json(), len(res.text)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('exchange')
    parser.add_argument('symbol')
    parser.add_argument('url')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='antelope')
    parser.add_argument('--interval', type=float, default=1)
    return parser.parse_args()


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    scraper_id = uuid.uuid4().hex

    while True:
        time_start = time.time()
        obj, size = get(args.url)
        time_end = time.time()
        time_elapsed = time_end - time_start
        logging.info(f'got {size} bytes in {time_elapsed:.2f} s')

        with open(f'/data/book-{args.exchange}-{args.symbol}-{scraper_id}', 'at') as f:
            data = json.dumps({
                'timestamp': time_end,
                'data': obj
            }, separators=(',', ':'))
            f.write(data + '\n')

        write_point(db, args.exchange, args.symbol, scraper_id, size, time_elapsed)
        time_remaining = max(0, args.interval - time_elapsed)
        random_delay = args.interval * random()
        time.sleep(time_remaining + random_delay)


if __name__ == '__main__':
    main()
