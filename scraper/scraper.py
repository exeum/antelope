#!/usr/bin/env python3

import argparse
import json
import logging
import ssl
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


def write_point(db, kind, exchange, base, quote, scraper_id, size):
    point = {
        'measurement': 'scraper',
        'tags': {
            'kind': kind,
            'exchange': exchange,
            'base': base,
            'quote': quote,
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


def wrap_data(data):
    return json.dumps({
        'timestamp': time.time(),
        'data': json.loads(data)
    }, separators=(',', ':'))


def append_line(filename, line):
    with open(filename, 'at') as f:
        f.write(line + '\n')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=('book', 'trades'))
    parser.add_argument('exchange')
    parser.add_argument('base')
    parser.add_argument('quote')
    parser.add_argument('url')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='antelope')
    parser.add_argument('--interval', type=float, default=1)
    parser.add_argument('--subscribe')
    return parser.parse_args()


def process(data, db, kind, exchange, base, quote, scraper_id):
    size = len(data)
    logging.info(f'got {size} bytes')
    write_point(db, kind, exchange, base, quote, scraper_id, size)
    date = time.strftime('%Y%m%d')
    filename = f'/data/{kind}-{exchange}-{base}-{quote}-{date}-{scraper_id}'
    append_line(filename, wrap_data(data))


# TODO: Refactor as metric tags?
def scrape_websocket(url, subscribe, db, kind, exchange, base, quote, scraper_id):
    logging.info(f'querying WebSocket endpoint {url}')
    ws = websocket.create_connection(url, sslopt={'cert_reqs': ssl.CERT_NONE})
    if subscribe:
        ws.send(subscribe)
    while True:
        data = ws.recv()
        if not data:
            logging.warning('skipping empty response')
            continue
        process(data, db, kind, exchange, base, quote, scraper_id)


def scrape_http(url, db, kind, exchange, base, quote, scraper_id, interval):
    logging.info(f'querying HTTP endpoint {url}')
    while True:
        time_start = time.time()
        data = http_get(url)
        process(data, db, kind, exchange, base, quote, scraper_id)
        time_elapsed = time.time() - time_start
        time_remaining = max(0, interval - time_elapsed)
        random_delay = interval * random()
        time.sleep(time_remaining + random_delay)


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    scraper_id = uuid.uuid4().hex
    if urlparse(args.url).scheme.startswith('ws'):
        scrape_websocket(args.url, args.subscribe, db, args.kind, args.exchange, args.base, args.quote, scraper_id)
    else:
        scrape_http(args.url, db, args.kind, args.exchange, args.base, args.quote, scraper_id, args.interval)


if __name__ == '__main__':
    main()
