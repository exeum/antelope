#!/usr/bin/env python3

import argparse
import json
import logging
import ssl
import time
import uuid

import influxdb
import requests
import websocket

TIMEOUT = 10


def process(data, db, kind, exchange, base, quote, scraper_id):
    size = len(data)
    logging.info(data)
    db.write_points([{
        'measurement': 'scraper',
        'tags': {
            'kind': kind,
            'exchange': exchange,
            'base': base,
            'quote': quote,
            'scraper_id': scraper_id
        },
        'time': int(time.time()) * 1000000000,
        'fields': {
            'size': size,
        }
    }])
    line = json.dumps({
        'timestamp': time.time(),
        'data': json.loads(data)
    }, separators=(',', ':'))
    date = time.strftime('%Y%m%d')
    filename = f'/data/{exchange}-{kind}-{base}-{quote}-{date}-{scraper_id}'
    with open(filename, 'at') as f:
        f.write(line + '\n')


def scrape(url, snapshot, subscribe, db, kind, exchange, base, quote):
    scraper_id = uuid.uuid4().hex
    if snapshot:
        logging.info(f'getting snapshot {snapshot}')
        data = requests.get(snapshot, timeout=TIMEOUT).text
        process(data, db, kind, exchange, base, quote, scraper_id)
    logging.info(f'scraping {url}')
    ws = websocket.create_connection(url, sslopt={'cert_reqs': ssl.CERT_NONE})
    if subscribe:
        logging.info(f'subscribing for {subscribe}')
        ws.send(subscribe)
    while True:
        data = ws.recv()
        if not data:
            logging.warning('skipping empty response')
            continue
        process(data, db, kind, exchange, base, quote, scraper_id)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('exchange')
    parser.add_argument('kind', choices=('book', 'trades'))
    parser.add_argument('base')
    parser.add_argument('quote')
    parser.add_argument('url')
    parser.add_argument('--subscribe')
    parser.add_argument('--snapshot')
    parser.add_argument('--influxdb')
    parser.add_argument('--database', default='antelope')
    return parser.parse_args()


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    db = influxdb.InfluxDBClient(host=args.influxdb, database=args.database, timeout=TIMEOUT)
    scrape(args.url, args.snapshot, args.subscribe, db, args.kind, args.exchange, args.base, args.quote)


if __name__ == '__main__':
    main()
