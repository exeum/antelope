#!/usr/bin/env python3

import gzip
import json
import time


def get_meta(fname) :
    return fname.split('-')

def get_entries(fname):
    with gzip.open(fname, 'r') as f :
        for line in f :
            yield json.loads(line.strip())

def zeroes(digits) :
    if digits == 0 :
        return ''
    return ('0' * digits)

def normalize_price(price, frac_digits) :
    tokens = price.split('.')
    if len(tokens) == 1 :
        return (price + '.' + zeroes(frac_digits))
    else :
        decimal = tokens[0]
        fraction = tokens[1]
        if len(fraction) < frac_digits :
            return (price + zeroes(frac_digits - len(fraction)))
        elif len(fraction) > frac_digits :
            return price[:(frac_digits - len(fraction))]
        else :
            return price

def yield_snapshot_book_gdax(fname, bids_limit = 50, asks_limit = 50) :
    bids = {}
    asks = {}
    timestamp = 0
    next_timestamp = 0
    returned_timestamp = 0
    unprocessed_update = None

    # entries generator
    entries_gen = get_entries(fname)

    # first line => fetch snapshot
    if timestamp == 0 :
        snapshot = next(entries_gen)
        if snapshot['data']['type'] == 'snapshot' :
            timestamp = int(snapshot['timestamp'])
            next_timestamp = timestamp + 1
            snapshot_bids = snapshot['data']['bids']
            snapshot_asks = snapshot['data']['asks']

            for (price, amount) in snapshot_bids :
                normed_price = normalize_price(price, 8)
                bids[normed_price] = amount
            for (price, amount) in snapshot_asks :
                normed_price = normalize_price(price, 8)
                asks[normed_price] = amount

    # iterate: ~ next_timestamp
    while True :
        update = unprocessed_update if unprocessed_update is not None else next(entries_gen)
        if update['data']['type'] != 'l2update' :
            pass
        else :
            timestamp = int(update['timestamp'])
            if timestamp < next_timestamp :
                unprocessed_update = None
                changes = update['data']['changes']
                for (side, price, amount) in changes :
                    normed_price = normalize_price(price, 8)
                    if side == 'buy' :
                        if amount == '0' :
                            del bids[normed_price]
                        else :
                            bids[normed_price] = amount
                    elif side == 'sell' :
                        if amount == '0' :
                            del asks[normed_price]
                        else :
                            asks[normed_price] = amount
            elif timestamp >= next_timestamp :
                returned_timestamp = next_timestamp
                unprocessed_update = update
                if timestamp == next_timestamp :
                    next_timestamp = timestamp + 1
                else :
                    next_timestamp = timestamp

                # yield
                sorted_bids = sorted(bids.items(), key = lambda key_value : float(key_value[0]), reverse = True)
                sorted_asks = sorted(asks.items(), key = lambda key_value : float(key_value[0]), reverse = False)
                returned_bids = sorted_bids[:bids_limit]
                returned_asks = sorted_asks[:asks_limit]

                yield (returned_timestamp, returned_bids, returned_asks)


def yield_snapshot_binance(fname, bids_limit, asks_limit) :
    return

def yield_snapshot_bitfinex(fname, bids_limit, asks_limit) :
    return


if __name__ == '''__main__''' :
    for (ts, bids, asks) in yield_snapshot_book_gdax(
        'gdax-book-btc-usd-20180324-cda678d6c28c454eafbb5dc31c56c354.gz', 5, 5) :
        print('timestamp:', ts)
        print('bids:', bids)
        print('asks:', asks)
        print('')
        time.sleep(1.0)
