#!/usr/bin/env bash
set -euxo pipefail

while true; do
    for f in $(ls orderbook-*[^gz] | grep -v $(date -u +%Y%m%d)); do
        gzip --best "$f"
    done
    sleep 60
done
