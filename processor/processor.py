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
BOOK_LIMIT = 50

tick = 0


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


def process_gdax_book_snapshot(snapshot):
    data = snapshot['data']
    bids = {normalize(price): amount for price, amount in data['bids']}
    asks = {normalize(price): amount for price, amount in data['asks']}
    return snapshot['timestamp'], bids, asks


def process_gdax_book(entries):
    unprocessed_update = None

    # first line => fetch snapshot
    timestamp, bids, asks = process_gdax_book_snapshot(next(entries))
    next_timestamp = timestamp + 1

    # iterate: ~ next_timestamp
    while True:
        update = unprocessed_update if unprocessed_update is not None else next(entries)
        if update['data']['type'] == 'l2update':
            timestamp = update['timestamp']
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
            else:
                returned_timestamp = next_timestamp
                unprocessed_update = update
                if timestamp == next_timestamp:
                    next_timestamp = timestamp + 1
                else:
                    next_timestamp = timestamp

                yield returned_timestamp, bids, asks


def process_bitfinex_book_snapshot(snapshot):
    bids = {}
    asks = {}
    data = snapshot['data'][1]
    for price, count, amount in data:
        if amount > 0:
            bids[normalize(price)] = str(amount)
        elif amount < 0:
            asks[normalize(price)] = str(amount)
    return snapshot['timestamp'], bids, asks


def process_bitfinex_book(entries):
    # discard two first lines (event:info and event:subscribed)
    next(entries)
    next(entries)

    unprocessed_update = None

    # first line => fetch snapshot
    timestamp, bids, asks = process_bitfinex_book_snapshot(next(entries))
    next_timestamp = timestamp + 1

    # iterate: ~ next_timestamp
    while True:
        update = unprocessed_update if unprocessed_update is not None else next(entries)
        timestamp = update['timestamp']
        if timestamp < next_timestamp:
            unprocessed_update = None
            changes = update['data']
            chanId, price, count, amount = update['data']
            normed_price = normalize(price)
            if amount > 0:  # bid
                if count == 0:
                    del bids[normed_price]
                else:
                    bids[normed_price] = str(amount)
            elif amount < 0:  # ask
                if count == 0:
                    del asks[normed_price]
                else:
                    asks[normed_price] = str(amount)
        else:
            returned_timestamp = next_timestamp
            unprocessed_update = update
            if timestamp == next_timestamp:
                next_timestamp = timestamp + 1
            else:
                next_timestamp = timestamp

            yield returned_timestamp, bids, asks


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
            yield entry['timestamp'], side, float(price), float(amount)


def process_book(entries, exchange):
    process = globals()[f'process_{exchange}_book']
    for timestamp, bids, asks in process(entries):
        for price, amount in sorted(bids.items(), reverse=True)[:BOOK_LIMIT]:
            yield timestamp, 'bid', float(price), float(amount)
        for price, amount in sorted(asks.items())[:BOOK_LIMIT]:
            yield timestamp, 'ask', float(price), float(amount)


def process(entries, db, exchange, kind, base, quote, scraper_id):
    global tick
    tick = 0
    process_entries = process_trades if 'trades' else process_book
    points = []
    for timestamp, side, price, amount in process_entries(entries, exchange):
        print(kind, timestamp, side, price, amount)
        points.append(make_point(kind, exchange, base, quote, side, timestamp, price, amount, scraper_id))
        if len(points) >= BATCH_SIZE:
            write_points(db, points)
            points = []
    write_points(db, points)


def read_entries(path):
    with gzip.open(path, 'rt') as f:
        for line in f:
            yield json.loads(line)


def handler(event, context):
    s3 = boto3.client('s3')
    db = influxdb.InfluxDBClient(host=os.environ['INFLUXDB'], database=DATABASE, timeout=TIMEOUT)
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        exchange, kind, base, quote, _, scraper_id = os.path.splitext(key)[0].split('-')
        path = os.path.join(tempfile.mkdtemp(), key)
        s3.download_file(bucket, key, path)
        entries = read_entries(path)
        process(entries, db, exchange, kind, base, quote, scraper_id)
