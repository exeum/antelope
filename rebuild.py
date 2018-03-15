#!/usr/bin/env python3

import argparse
import gzip
import json
import logging
from pathlib import Path

import influxdb

TIMEOUT = 5


# Gemini, Bitfinex
def get_prices_type1(obj):
    return ({float(order['price']) for order in obj['bids']},
            {float(order['price']) for order in obj['asks']})


# Binance, Okex, GDAX
def get_prices_type2(obj):
    return ({float(order[0]) for order in obj['bids']},
            {float(order[0]) for order in obj['asks']})


def make_point(exchange, base, quote, side, timestamp, price):
    return {
        'measurement': 'price',
        'tags': {
            'exchange': exchange,
            'base': base,
            'quote': quote,
            'side': side
        },
        'time': int(timestamp) * 1000000000,
        'fields': {
            'price': price
        }
    }


def write_points(db, points):
    if points:
        logging.info(f'writing {len(points)} points')
        db.write_points(points)


def parse_archive_filename(filename):
    kind, exchange, base, quote, date, scraper_id = Path(filename).stem.split('-')
    return exchange, base, quote, scraper_id


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', default='/data')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='antelope')
    parser.add_argument('--batch-size', type=int, default=1000)
    return parser.parse_args()


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    for path in Path(args.dir).glob('*[!.gz]'):
        exchange, base, quote, scraper_id = parse_archive_filename(path)
        get_prices = {
            'gemini': get_prices_type1,
            'bitfinex': get_prices_type1,
            'binance': get_prices_type2,
            'okex': get_prices_type2,
            'gdax': get_prices_type2
        }[exchange]
        logging.info(f'processing {exchange} {base}/{quote} ({scraper_id})')
        with gzip.open(path, 'rt') as f:
            points = []
            for line in f:
                    obj = json.loads(line)
                    bids, asks = get_prices(obj['data'])
                    points.extend([make_point(exchange, base, quote, 'bid', obj['timestamp'], max(bids)),
                                   make_point(exchange, base, quote, 'ask', obj['timestamp'], max(asks))])
                    if len(points) >= args.batch_size:
                        write_points(db, points)
                        points = []
            write_points(db, points)


if __name__ == '__main__':
    main()
