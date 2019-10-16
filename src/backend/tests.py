#!/usr/bin/env python
import unittest


def test(a, b, c, **kwargs):
    print(a)
    print(b)
    print(kwargs)


if __name__ == '__main__':
    td = {}
    td['aa'] = 22
    d = {}
    d['b'] = 33
    d['c'] = 44
    test(td, **d, **td)
