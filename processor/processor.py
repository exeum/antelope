#!/usr/bin/env python3

import decimal
import gzip
import tempfile
import json
import logging
import os

import boto3
import influxdb

DATABASE = 'antelope'
TIMEOUT = 10
BATCH_SIZE = 1000


# https://docs.bitfinex.com/v1/reference#ws-public-trades
def process_bitfinex_trades_entry(entry):
    if entry[1] == 'te':
        side = 'sell' if entry[5] < 0 else 'buy'
        yield side, entry[4], abs(entry[5])


# https://docs.gdax.com/#the-code-classprettyprintmatchescode-channel
def process_gdax_trades_entry(entry):
    yield entry['side'], float(entry['price']), float(entry['size'])


def normalize(x):
    return decimal.Decimal(str(x)).normalize()


def process_gdax_book(entries):
    bids = {}
    asks = {}
    next_timestamp = 0
    unprocessed_update = None

    # first line => fetch snapshot
    snapshot = next(entries)
    if snapshot['data']['type'] == 'snapshot':
        timestamp = int(snapshot['timestamp'])
        next_timestamp = timestamp + 1
        snapshot_bids = snapshot['data']['bids']
        snapshot_asks = snapshot['data']['asks']

        for (price, amount) in snapshot_bids:
            normed_price = normalize(price)
            bids[normed_price] = amount
        for (price, amount) in snapshot_asks:
            normed_price = normalize(price)
            asks[normed_price] = amount

    # iterate: ~ next_timestamp
    while True:
        update = unprocessed_update if unprocessed_update is not None else next(entries)
        if update['data']['type'] != 'l2update':
            pass
        else:
            timestamp = int(update['timestamp'])
            if timestamp < next_timestamp:
                unprocessed_update = None
                changes = update['data']['changes']
                for (side, price, amount) in changes:
                    normed_price = normalize(price)
                    if side == 'buy':
                        if amount == '0':
                            del bids[normed_price]
                        else:
                            bids[normed_price] = amount
                    elif side == 'sell':
                        if amount == '0':
                            del asks[normed_price]
                        else:
                            asks[normed_price] = amount
            elif timestamp >= next_timestamp:
                returned_timestamp = next_timestamp
                unprocessed_update = update
                if timestamp == next_timestamp:
                    next_timestamp = timestamp + 1
                else:
                    next_timestamp = timestamp

                yield returned_timestamp, set(bids.items()), set(asks.items())


def make_point(kind, exchange, base, quote, side, timestamp, price, amount, scraper_id):
    global tick
    tick += 1
    return {
        'measurement': kind,
        'tags': {
            'exchange': exchange,
            'base': base,
            'quote': quote,
            'side': side,
            'scraper_id': scraper_id
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


def process_trades(entries, exchange):
    process_entry = globals()[f'process_{exchange}_trades_entry']
    for entry in entries:
        for side, price, amount in process_entry(entry['data']):
            yield entry['timestamp'], side, price, amount


def process_book(entries, exchange):
    process = globals()[f'process_{exchange}_book']
    for timestamp, bids, asks in process(entries):
        for price, amount in bids.items():
            yield timestamp, 'bid', price, amount
        for price, amount in asks.items():
            yield timestamp, 'ask', price, amount


def foo(entries, db, exchange, kind, base, quote, scraper_id):
    process = process_trades if 'trades' else process_book
    points = []
    for timestamp, side, price, amount in process(entries, exchange):
        print(kind, timestamp, side, price, amount)
        points.append(make_point(kind, exchange, base, quote, side, timestamp, price, amount, scraper_id))
        if len(points) >= BATCH_SIZE:
            write_points(db, points)
            points = []
    write_points(db, points)


def read_entries(path):
    with gzip.open(path, 'r') as f:
        for line in f:
            yield json.loads(line)


def handler(event, context):
    s3 = boto3.client('s3')
    db = influxdb.InfluxDBClient(host=os.environ['INFLUXDB'], database=DATABASE, timeout=TIMEOUT)
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        exchange, kind, base, quote, _, scraper_id = os.path.splitext(key)[0]
        path = os.path.join(tempfile.mkdtemp(), key)
        s3.download_file(bucket, key, path)
        entries = read_entries(path)
        foo(entries, db, exchange, kind, base, quote, scraper_id)
