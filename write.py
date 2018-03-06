#!/usr/bin/env python3

import argparse
import gzip
import json
import pathlib

import influxdb

TIMEOUT = 5


# Gemini, Bitfinex
def get_prices_type1(obj):
    return ({float(order['price']) for order in obj['bids']},
            {float(order['price']) for order in obj['asks']})


# Binance, Okex
def get_prices_type2(obj):
    return ({float(order[0]) for order in obj['bids']},
            {float(order[0]) for order in obj['asks']})


def write_points(db, points):
    if points:
        print(f'writing {len(points)} points')
        db.write_points(points, time_precision='s')


def parse_archive_filename(filename):
    _, exchange, symbol, _, crawler_id = pathlib.Path(filename).stem.split('-')
    return exchange, symbol, crawler_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archives', nargs='+')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='prices')
    parser.add_argument('--batch-size', type=int, default=10000)
    args = parser.parse_args()
    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    for filename in args.archives:
        exchange, symbol, crawler_id = parse_archive_filename(filename)
        get_prices = {
            'gemini': get_prices_type1,
            'bitfinex': get_prices_type1,
            'binance': get_prices_type2,
            'okex': get_prices_type2
        }[exchange]
        print(f'processing {exchange} {symbol} ({crawler_id})')
        with gzip.open(filename, 'rt') as f:
            points = []
            for line in f:
                obj = json.loads(line)
                ts = obj['__timestamp__']
                bids, asks = get_prices(obj)
                points.append({
                    'measurement': 'price',
                    'tags': {
                        'exchange': exchange,
                        'symbol': symbol
                    },
                    'time': int(ts),
                    'fields': {
                        'bid': max(bids),
                        'ask': min(asks)
                    }
                })
                if len(points) >= args.batch_size:
                    write_points(db, points)
                    points = []
            write_points(db, points)


if __name__ == '__main__':
    main()
