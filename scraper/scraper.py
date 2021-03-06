#!/usr/bin/env python3

import argparse
import json
import logging
import queue
import ssl
import threading
import time
import uuid

import influxdb
import requests
import websocket

TIMEOUT = 30
RETRIES = 10
QUEUE_SIZE = 10000

points = queue.Queue(maxsize=QUEUE_SIZE)


def write_points(db):
    while True:
        try:
            db.write_points([points.get()])
        except Exception:
            logging.warning("unable to write point")
            time.sleep(TIMEOUT)


def process(data, kind, exchange, base, quote, scraper_id):
    size = len(data)
    logging.info(data)
    timestamp = time.time()
    try:
        points.put_nowait(
            {
                "measurement": "scraper",
                "tags": {
                    "kind": kind,
                    "exchange": exchange,
                    "base": base,
                    "quote": quote,
                    "scraper_id": scraper_id,
                },
                "time": int(timestamp * 1_000_000_000),
                "fields": {"size": size},
            }
        )
    except queue.Full:
        logging.warning("queue full; skipping")
    line = json.dumps(
        {"timestamp": int(timestamp), "data": json.loads(data)}, separators=(",", ":")
    )
    date = time.strftime("%Y%m%d")
    filename = f"/data/{exchange}-{kind}-{base}-{quote}-{date}-{scraper_id}"
    with open(filename, "at") as f:
        f.write(line + "\n")


def start_thread(target, args):
    thread = threading.Thread(target=target, args=args)
    thread.daemon = True
    thread.start()


def http_get(url):
    logging.info(f"getting {url}")
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def read(url, subscribe, snapshot):
    if snapshot:
        yield http_get(snapshot)
    logging.info(f"connecting to {url}")
    ws = websocket.create_connection(
        url, timeout=TIMEOUT, sslopt={"cert_reqs": ssl.CERT_NONE}
    )
    if subscribe:
        logging.info(f"sending {subscribe}")
        ws.send(subscribe)
    logging.info("receiving data")
    while True:
        data = ws.recv()
        if not data:
            logging.warning("skipping empty response")
            continue
        yield data


def scrape(url, subscribe, snapshot, kind, exchange, base, quote):
    scraper_id = uuid.uuid4().hex
    logging.info(f"scraping {exchange} {base}/{quote} {kind} ({scraper_id})")
    retry_count = 0
    while retry_count < RETRIES:
        try:
            for data in read(url, subscribe, snapshot):
                process(data, kind, exchange, base, quote, scraper_id)
                retry_count = 0
        except Exception:
            retry_count += 1
            logging.exception(f"{retry_count}/{RETRIES} retries")
    raise RuntimeError("too many retries")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("exchange")
    parser.add_argument("kind", choices=("book", "trades"))
    parser.add_argument("base")
    parser.add_argument("quote")
    parser.add_argument("url")
    parser.add_argument("--subscribe")
    parser.add_argument("--snapshot")
    parser.add_argument("--influxdb")
    parser.add_argument("--database", default="antelope")
    return parser.parse_args()


def main():
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.INFO)
    args = parse_args()
    db = influxdb.InfluxDBClient(
        host=args.influxdb, database=args.database, timeout=TIMEOUT
    )
    start_thread(write_points, (db,))
    scrape(
        args.url,
        args.subscribe,
        args.snapshot,
        args.kind,
        args.exchange,
        args.base,
        args.quote,
    )


if __name__ == "__main__":
    main()
