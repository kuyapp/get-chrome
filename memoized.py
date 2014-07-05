#!/usr/bin/env python
# -*- coding:utf-8 -*-

import time
import functools


class Memoized(object):
    def __init__(self, func, duration=60):
        self.func = func
        self.duration = duration
        self.timeStamp = 0
        self.cache = {}

    def __call__(self, *args):
        timeout = self.timeStamp + self.duration < time.time()
        if args not in self.cache or timeout:
            value = self.func(*args)
            self.cache[args] = value
            self.timeStamp = time.time()
            return value
        else:
            return self.cache[args]

    def __repr__(self):
        return self.func.__doc__

    def __get__(self, obj):
        return functools.partial(self.__call__, obj)
