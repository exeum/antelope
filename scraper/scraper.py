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


def write_point(db, tags, size):
    db.write_points([{
        'measurement': 'scraper',
        'tags': tags,
        'time': int(time.time()) * 1000000000,
        'fields': {
            'size': size,
        }
    }])


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


def process(data, db, tags, filename):
    size = len(data)
    logging.info(f'got {size} bytes')
    write_point(db, tags, size)
    line = json.dumps({
        'timestamp': time.time(),
        'data': json.loads(data)
    }, separators=(',', ':'))
    with open(filename, 'at') as f:
        f.write(line + '\n')


@retry(stop_max_attempt_number=RETRIES)
def scrape_websocket(url, db, tags, filename, subscribe):
    logging.info(f'scraping WebSocket endpoint {url}')
    ws = websocket.create_connection(url, sslopt={'cert_reqs': ssl.CERT_NONE})
    if subscribe:
        ws.send(subscribe)
    while True:
        data = ws.recv()
        if not data:
            logging.warning('skipping empty response')
            continue
        process(data, db, tags, filename)


@retry(stop_max_attempt_number=RETRIES)
def scrape_http(url, db, tags, filename, interval):
    logging.info(f'scraping HTTP endpoint {url}')
    while True:
        time_start = time.time()
        data = requests.get(url, timeout=TIMEOUT).text
        process(data, db, tags, filename)
        time_elapsed = time.time() - time_start
        time_remaining = max(0, interval - time_elapsed)
        random_delay = interval * random()
        time.sleep(time_remaining + random_delay)


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    scraper_id = uuid.uuid4().hex
    date = time.strftime('%Y%m%d')
    filename = f'/data/{args.kind}-{args.exchange}-{args.base}-{args.quote}-{date}-{scraper_id}'
    tags = {
        'kind': args.kind,
        'exchange': args.exchange,
        'base': args.base,
        'quote': args.quote,
        'scraper_id': scraper_id
    }
    if urlparse(args.url).scheme.startswith('ws'):
        scrape_websocket(args.url, db, tags, filename, args.subscribe)
    else:
        scrape_http(args.url, db, tags, filename, args.interval)


if __name__ == '__main__':
    main()
