#!/usr/bin/env python3

import argparse
import json
import logging
import time
import uuid

import influxdb
import websocket

TIMEOUT = 10


def write_point(db, exchange, symbol, scraper_id, size):
    point = {
        'measurement': 'trades',
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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('exchange')
    parser.add_argument('symbol')
    parser.add_argument('websocket')
    parser.add_argument('request')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='antelope')
    return parser.parse_args()


def wrap_data(data):
    return json.dumps({
        'timestamp': time.time(),
        'data': json.loads(data)
    }, separators=(',', ':'))


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    scraper_id = uuid.uuid4().hex

    filename = f'/data/trades-{args.exchange}-{args.symbol}-{scraper_id}'
    ws = websocket.create_connection(args.websocket)
    if args.request:
        ws.send(args.request)
    while True:
        data = ws.recv()
        size = len(data)
        logging.info(f'got {size} bytes')
        write_point(db, args.exchange, args.symbol, scraper_id, size)
        with open(filename, 'at') as f:
            f.write(wrap_data(data) + '\n')


if __name__ == '__main__':
    main()
