# antelope

[![Build Status](https://travis-ci.org/exeum/antelope.svg?branch=master)](https://travis-ci.org/exeum/antelope) [![Maintainability](https://api.codeclimate.com/v1/badges/8318af4aa11126b65f50/maintainability)](https://codeclimate.com/github/exeum/antelope/maintainability)

Antelope is a fast, scaleable and fault-tolerant system for collecting, processing and storing market data from multiple cryptocurrency exchanges. It aims to be as simple as possible.

## Test

```
python -m pytest
```

## Deploy

```
make deploy INFLUXDB=<influxdb-host> AWS_ACCESS_KEY_ID=<access-key-id> AWS_SECRET_ACCESS_KEY=<secret-access-key>
```
