#!/usr/bin/env python3

import argparse
import json
import sys


# Gemini, Bitfinex
def parse_orderbook_type1(obj):
    for bid in obj['bids']:
        yield obj['__timestamp__'], 'bid', bid['price'], bid['amount']
    for bid in obj['asks']:
        yield obj['__timestamp__'], 'ask', bid['price'], bid['amount']


# Binance, Okex
def parse_orderbook_type2(obj):
    for bid in obj['bids']:
        yield obj['__timestamp__'], 'bid', bid[0], bid[1]
    for bid in obj['asks']:
        yield obj['__timestamp__'], 'ask', bid[0], bid[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exchange')
    args = parser.parse_args()
    funcs = {
        'gemini': parse_orderbook_type1,
        'bitfinex': parse_orderbook_type1,
        'binance': parse_orderbook_type2,
        'okex': parse_orderbook_type2
    }
    for line in sys.stdin:
        obj = json.loads(line)
        for order in funcs[args.exchange](obj):
            print(','.join(map(str, order)))


if __name__ == '__main__':
    main()
