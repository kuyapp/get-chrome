#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import time
from werkzeug.contrib.cache import MemcachedCache
from pylibmc import Client

current_milli_time = lambda: int(round(time.time() * 1000))


class Memoized(object):

    def __init__(self, func):
        memcache_servers = os.environ.get('MEMCACHIER_SERVERS', '')
        memcache_username = os.environ.get('MEMCACHIER_USERNAME', '')
        memcache_password = os.environ.get('MEMCACHIER_PASSWORD', '')
        if memcache_servers:
            client = Client([memcache_servers], behaviors={"tcp_nodelay": True},
                            binary=True, username=memcache_username, password=memcache_password)
        else:
            client = Client(['127.0.0.1:11211'])
        self.cache = MemcachedCache(client, default_timeout=60)
        self.func = func

    def __call__(self, *args):
        start_time = current_milli_time()
        value = self.cache.get(*args)
        if value is None:
            value = self.func(*args)
            self.cache.set(args[0], value)
            print 'miss', args[0]
        else:
            print 'hit ', args[0]
        end_time = current_milli_time()

        print 'cost {time}'.format(time=end_time-start_time)
        return value
