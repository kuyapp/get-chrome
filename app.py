#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import urllib2
from functools import wraps
from collections import OrderedDict
from pylibmc import Client
from werkzeug.contrib.cache import MemcachedCache
from flask import Flask, request, render_template, redirect
from xml.etree.ElementTree import fromstring

app = Flask(__name__)

API_URL = 'http://tools.google.com/service/update2'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_STATIC = os.path.join(APP_ROOT, 'static')
MEMCACHE_SERVERS =  os.environ.get('MEMCACHIER_SERVERS', '')
MEMCACHE_USERNAME = os.environ.get('MEMCACHIER_USERNAME', '')
MEMCACHE_PASSWORD = os.environ.get('MEMCACHIER_PASSWORD', '')

with open(os.path.join(APP_STATIC, 'post_data_stable.xml')) as f:
    POST_DATA_STABLE = f.read().replace('\n', '')

with open(os.path.join(APP_STATIC, 'post_data_beta.xml')) as f:
    POST_DATA_BETA = f.read().replace('\n', '')

with open(os.path.join(APP_STATIC, 'post_data_dev.xml')) as f:
    POST_DATA_DEV = f.read().replace('\n', '')

post_data = OrderedDict([('stable', POST_DATA_STABLE),
                         ('beta', POST_DATA_BETA),
                         ('dev', POST_DATA_DEV)])

if MEMCACHE_SERVERS:
    client = Client([MEMCACHE_SERVERS], behaviors={"tcp_nodelay": True},
                    binary=True, username=MEMCACHE_USERNAME, password=MEMCACHE_PASSWORD)
else:
    client = Client(['127.0.0.1:11211'])
cache = MemcachedCache(client, default_timeout=60)


def cached(timeout=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            key = args[0]
            rv = cache.get(key)
            if rv is not None:
                print 'hit\t\t', key
                return rv
            print 'miss\t\t', key
            rv = f(*args, **kwargs)
            cache.set(key, rv, timeout=timeout)
            return rv
        return decorated_function
    return decorator


@cached()
def get_response(channel):
    req = urllib2.Request(API_URL, post_data[channel])
    r = urllib2.urlopen(req).read()
    root = fromstring(r)
    package = root.find('app/updatecheck/manifest/packages/package').attrib['name']
    return [i.attrib['codebase'] + package for i in root.findall('app/updatecheck/urls/url')]


@app.route('/')
@app.route('/channel/')
@app.route('/channel/<channel>')
def show_link(channel='stable'):
    links = OrderedDict()
    for key in post_data.iterkeys():
        if channel == key or channel == 'all':
            links[key] = get_response(key)
    if links:
        return render_template('index.html', links=links)
    else:
        return redirect('/channel/stable')

if __name__ == '__main__':
    from werkzeug.contrib.profiler import ProfilerMiddleware
    f = open('profiler.log', 'w')
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, f)
    app.run(host='0.0.0.0', debug=True)
