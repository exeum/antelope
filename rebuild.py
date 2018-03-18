#!/usr/bin/env python3

import argparse
import gzip
import json
import logging
from pathlib import Path

import influxdb

TIMEOUT = 5

# Dirty hack to avoid InfluxDB overwriting metrics
tick = 0


# https://docs.bitfinex.com/v1/reference#ws-public-trades
def normalize_trades_entry_bitfinex(obj):
    if obj[1] == 'te':
        side = 'sell' if obj[5] < 0 else 'buy'
        yield side, obj[4], abs(obj[5])


# https://docs.gdax.com/#the-code-classprettyprintmatchescode-channel
def normalize_trades_entry_gdax(obj):
    yield obj['side'], float(obj['price']), float(obj['size'])


# https://bitfinex.readme.io/v1/reference#rest-public-fundingbook
# Same for Gemini
def normalize_book_entry_bitfinex(obj):
    for order in obj['bids']:
        yield 'buy', float(order['price']), float(order['amount'])
    for order in obj['asks']:
        yield 'sell', float(order['price']), float(order['amount'])


# https://docs.gdax.com/#get-product-order-book
# Same for Binance, Okex
def normalize_book_entry_gdax(obj):
    for order in obj['bids']:
        yield 'buy', float(order[0]), float(order[1])
    for order in obj['asks']:
        yield 'sell', float(order[0]), float(order[1])


def make_point(kind, exchange, base, quote, side, timestamp, price, amount):
    global tick
    tick += 1
    return {
        'measurement': kind,
        'tags': {
            'exchange': exchange,
            'base': base,
            'quote': quote,
            'side': side
        },
        'time': (int(timestamp) * 1000000000) + tick,
        'fields': {
            'price': price,
            'amount': amount
        }
    }


def write_points(db, points):
    if points:
        logging.info(f'writing {len(points)} points')
        db.write_points(points)


def parse_archive_filename(filename):
    kind, exchange, base, quote, date, scraper_id = Path(filename).stem.split('-')
    return kind, exchange, base, quote, scraper_id


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('archives', nargs='+')
    parser.add_argument('--host', default='107.191.60.146')
    parser.add_argument('--database', default='antelope')
    parser.add_argument('--batch-size', type=int, default=1000)
    return parser.parse_args()


def main():
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)
    args = parse_args()
    db = influxdb.InfluxDBClient(host=args.host, database=args.database, timeout=TIMEOUT)
    points = []
    for filename in args.archives:
        kind, exchange, base, quote, scraper_id = parse_archive_filename(filename)
        logging.info(f'processing {exchange} {base}/{quote} {kind} ({scraper_id})')
        normalize_entry = globals()[f'normalize_{kind}_entry_{exchange}']
        with gzip.open(filename, 'rt') as f:
            for line in f:
                obj = json.loads(line)
                timestamp, data = obj['timestamp'], obj['data']
                try:
                    for side, price, amount in normalize_entry(data):
                        points.append(make_point(kind, exchange, base, quote, side, timestamp, price, amount))
                except Exception:
                    logging.warning('skipping %s', data)
                if len(points) >= args.batch_size:
                    write_points(db, points)
                    points = []
            write_points(db, points)


if __name__ == '__main__':
    main()
