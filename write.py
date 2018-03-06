#!/usr/bin/env python3

import argparse
import json
import sys

import influxdb

TIMEOUT = 5


# Gemini, Bitfinex
def get_prices_type1(obj):
    return {order['price'] for order in obj['bids']}, {order['price'] for order in obj['asks']}


# Binance, Okex
def get_prices_type2(obj):
    return {order[0] for order in obj['bids']}, {order[0] for order in obj['asks']}


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exchange')
    parser.add_argument('symbol')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='prices')
    parser.add_argument('--batch-size', type=int, default=5000)
    args = parser.parse_args()

    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    get_prices = {
        'gemini': get_prices_type1,
        'bitfinex': get_prices_type1,
        'binance': get_prices_type2,
        'okex': get_prices_type2
    }

    points = []
    for line in sys.stdin:
        obj = json.loads(line)
        ts = obj['__timestamp__']
        bids, asks = get_prices[args.exchange](obj)
        bid = make_point(args.exchange, args.symbol, 'bid', ts, max(bids))
        ask = make_point(args.exchange, args.symbol, 'ask', ts, min(asks))
        points.extend([bid, ask])
        if len(points) >= args.batch_size:
            write_points(db, points)
            points = []
    write_points(db, points)


if __name__ == '__main__':
    main()
