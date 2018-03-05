#!/usr/bin/env python3

import argparse
import json
import threading
import time
import uuid

import influxdb
import requests


def write_metric(db, measurement, k, v):
    db.write_points([
        {
            'measurement': measurement,
            'time': int(time.time()),
            'fields': {
                k: float(v)
            }
        }
    ], time_precision='s')


def start_thread(target, args):
    thread = threading.Thread(target=target, args=args)
    thread.daemon = True
    thread.start()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exchange')
    parser.add_argument('symbol')
    parser.add_argument('url')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='crawler')
    parser.add_argument('--timeout', type=int, default=10)
    parser.add_argument('--interval', type=float, default=1)
    args = parser.parse_args()

    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=args.timeout)
    crawler_id = uuid.uuid4().hex

    while True:
        time_start = time.time()
        res = requests.get(args.url, timeout=args.timeout)
        size = len(res.text)
        obj = res.json()
        time_end = time.time()
        time_elapsed = time_end - time_start

        obj['__timestamp__'] = int(time_end)
        data = json.dumps(obj, separators=(',', ':'))

        date = time.strftime('%Y%m%d')
        with open(f'data/orderbook-{args.exchange}-{args.symbol}-{date}-{crawler_id}', 'a') as f:
            f.write(data + '\n')

        k = f'{args.exchange}_{args.symbol}_{crawler_id[:4]}'
        start_thread(write_metric, (db, 'orderbook_size', k, size))
        start_thread(write_metric, (db, 'orderbook_latency', k, time_elapsed))

        print(f'got {size} bytes in {time_elapsed:.2f} s')
        time.sleep(max(0, args.interval - time_elapsed))


if __name__ == '__main__':
    main()
