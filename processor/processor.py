#!/usr/bin/env python3

import decimal


def normalize(x):
    return decimal.Decimal(str(x)).normalize()
