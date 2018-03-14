#!/usr/bin/env python3

import argparse
import json
import logging
import time
import uuid
from random import random
from urllib.parse import urlparse

import influxdb
import requests
import websocket
from retrying import retry

TIMEOUT = 5
RETRIES = 3


def time_ns():
    return int(time.time() * 1000000000)


def write_point(db, kind, exchange, symbol, scraper_id, size):
    point = {
        'measurement': 'scraper',
        'tags': {
            'kind': kind,
            'exchange': exchange,
            'symbol': symbol,
            'scraper_id': scraper_id
        },
        'time': time_ns(),
        'fields': {
            'size': float(size),
        }
    }
    db.write_points([point])


@retry(stop_max_attempt_number=RETRIES)
def http_get(url):
    return requests.get(url, timeout=TIMEOUT).text


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=('book', 'trades'))
    parser.add_argument('exchange')
    parser.add_argument('symbol')
    parser.add_argument('uri')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='antelope')
    parser.add_argument('--interval', type=float, default=1)
    parser.add_argument('--subscribe')
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

    if urlparse(args.uri).scheme.startswith('ws'):
        logging.info(f'querying WebSocket endpoint {args.uri}')
        ws = websocket.create_connection(args.uri)
        if args.subscribe:
            ws.send(args.subscribe)
        while True:
            data = ws.recv()

            size = len(data)
            logging.info(f'got {size} bytes')
            write_point(db, args.kind, args.exchange, args.symbol, scraper_id, size)
            date = time.strftime('%Y%m%d')
            filename = f'/data/{args.kind}-{args.exchange}-{args.symbol}-{date}-{scraper_id}'
            append_line(filename, wrap_data(data))
    else:
        logging.info(f'querying REST endpoint {args.uri}')
        while True:
            data = http_get(args.uri)

            size = len(data)
            logging.info(f'got {size} bytes')
            write_point(db, args.kind, args.exchange, args.symbol, scraper_id, size)
            date = time.strftime('%Y%m%d')
            filename = f'/data/{args.kind}-{args.exchange}-{args.symbol}-{date}-{scraper_id}'
            append_line(filename, wrap_data(data))

            random_delay = args.interval * random()
            time.sleep(args.interval + random_delay)


if __name__ == '__main__':
    main()
