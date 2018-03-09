# antelope

[![Build Status](https://travis-ci.org/exeum/antelope.svg?branch=master)](https://travis-ci.org/exeum/antelope) [![Maintainability](https://api.codeclimate.com/v1/badges/8318af4aa11126b65f50/maintainability)](https://codeclimate.com/github/exeum/antelope/maintainability)

Antelope is a fast, scaleable and fault-tolerant system for collecting, processing and storing market data from multiple cryptocurrency exchanges. It aims to be as simple as possible.

## Overview

Objective: get per-second market data for a large number of exchanges and currency pairs.

Scrapers write raw order book data to logs (rotated daily), and deliverers send compressed logs from previous days to S3 (simply gzipping the logs makes them around 10x smaller). They run in a Docker swarm, and are organised in a way that minimizes the number of scrapers for an exchange on on any one host (to avoid API rate limitng). Scrapers are replicated just in case.

Data in S3 is parsed and passed forward for consumption. Easily visualizable data (e.g. market prices) goes to InfluxDB; order book data goes to TimescaleDB. Make all entries unique and just push everything.

No need for complex redundancy setups since the raw data is safely in S3. Databases can be rebuilt with a single command in case of apocalypse.

## Data storage

Order book archives are stored in S3 as `orderbook-<exchange>-<symbol>-<yyyymmdd>-<uuid>.gz`.
