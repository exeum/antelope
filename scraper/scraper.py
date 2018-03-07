#!/usr/bin/env python3

import argparse
import json
import time
import uuid

import influxdb
import requests
from retrying import retry

TIMEOUT = 5
RETRIES = 3


def write_point(db, exchange, symbol, crawler_id, size, latency):
    point = {
        'measurement': 'orderbook',
        'tags': {
            'exchange': exchange,
            'symbol': symbol,
            'id': crawler_id
        },
        'time': int(time.time()),
        'fields': {
            'size': float(size),
            'latency': float(latency)
        }
    }
    db.write_points([point], time_precision='s')


@retry(stop_max_attempt_number=RETRIES)
def get(url):
    res = requests.get(url, timeout=TIMEOUT)
    return res.json(), len(res.text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exchange')
    parser.add_argument('symbol')
    parser.add_argument('url')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='antelope')
    parser.add_argument('--interval', type=float, default=1)
    args = parser.parse_args()

    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    crawler_id = uuid.uuid4().hex

    while True:
        time_start = time.time()
        obj, size = get(args.url)
        time_end = time.time()
        time_elapsed = time_end - time_start

        obj['__timestamp__'] = int(time_end)
        data = json.dumps(obj, separators=(',', ':'))

        date = time.strftime('%Y%m%d')
        with open(f'data/orderbook-{args.exchange}-{args.symbol}-{date}-{crawler_id}', 'at') as f:
            f.write(data + '\n')

        write_point(db, args.exchange, args.symbol, crawler_id, size, time_elapsed)

        print(f'got {size} bytes in {time_elapsed:.2f} s')
        time.sleep(max(0, args.interval - time_elapsed))


if __name__ == '__main__':
    main()
