#!/usr/bin/env python3

import argparse
import gzip
import json
import pathlib

import influxdb

TIMEOUT = 5


# Gemini, Bitfinex
def get_prices_type1(obj):
    return ({order['price'] for order in obj['bids']},
            {order['price'] for order in obj['asks']})


# Binance, Okex
def get_prices_type2(obj):
    return ({order[0] for order in obj['bids']},
            {order[0] for order in obj['asks']})


def write_points(db, points):
    if points:
        print(f'writing {len(points)} points')
        db.write_points(points, time_precision='s')


def make_point(exchange, symbol, kind, ts, price):
    return {
        'measurement': f'{exchange}_{symbol}',
        'tags': {
            'kind': kind
        },
        'time': int(ts),
        'fields': {
            'price': float(price)
        }
    }


def parse_archive_filename(filename):
    tokens = pathlib.Path(filename).stem.split('-')
    return tokens[1], tokens[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='prices')
    parser.add_argument('--batch-size', type=int, default=5000)
    args = parser.parse_args()

    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    exchange, symbol = parse_archive_filename(args.archive)
    get_prices = {
        'gemini': get_prices_type1,
        'bitfinex': get_prices_type1,
        'binance': get_prices_type2,
        'okex': get_prices_type2
    }[exchange]
    points = []

    with gzip.open(args.archive, 'rt') as f:
        for line in f:
            obj = json.loads(line)
            ts = obj['__timestamp__']
            bids, asks = get_prices(obj)
            bid = make_point(exchange, symbol, 'bid', ts, max(bids))
            ask = make_point(exchange, symbol, 'ask', ts, min(asks))
            points.extend([bid, ask])
            if len(points) >= args.batch_size:
                write_points(db, points)
                points = []
        write_points(db, points)


if __name__ == '__main__':
    main()
