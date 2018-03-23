#!/usr/bin/env python3

import argparse
import json
import logging
import ssl
import time
import uuid

import influxdb
import websocket

TIMEOUT = 10


def write_point(db, tags, size):
    db.write_points([{
        'measurement': 'scraper',
        'tags': tags,
        'time': int(time.time()) * 1000000000,
        'fields': {
            'size': size,
        }
    }])


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


def scrape(url, db, tags, filename, subscribe):
    logging.info(f'scraping {url}')
    ws = websocket.create_connection(url, sslopt={'cert_reqs': ssl.CERT_NONE})
    if subscribe:
        ws.send(subscribe)
    while True:
        data = ws.recv()
        if not data:
            logging.warning('skipping empty response')
            continue
        process(data, db, tags, filename)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=('book', 'trades'))
    parser.add_argument('exchange')
    parser.add_argument('base')
    parser.add_argument('quote')
    parser.add_argument('url')
    parser.add_argument('--subscribe')
    parser.add_argument('--host', default='18.216.124.51')
    parser.add_argument('--database', default='antelope')
    return parser.parse_args()


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
    scrape(args.url, db, tags, filename, args.subscribe)


if __name__ == '__main__':
    main()
