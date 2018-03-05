#!/usr/bin/env python3

import argparse
import sys

import influxdb


def write_points(db, points):
    if points:
        print(f'writing {len(points)} points')
        db.write_points(points, time_precision='s')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exchange')
    parser.add_argument('symbol')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='test')
    parser.add_argument('--batch-size', type=int, default=5000)
    args = parser.parse_args()

    db = influxdb.InfluxDBClient(host=args.host, database=args.database)
    points = []
    for line in sys.stdin:
        ts, kind, price, amount = line.split(',')
        points.append({
            'measurement': f'{args.exchange}_{args.symbol}',
            'tags': {
                'kind': kind
            },
            'time': int(ts),
            'fields': {
                'price': float(price),
                'amount': float(amount)
            }
        })
        if len(points) == args.batch_size:
            write_points(db, points)
            points = []
    write_points(db, points)


if __name__ == '__main__':
    main()
