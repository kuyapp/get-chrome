#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import sys
from collections import OrderedDict
from xml.etree.ElementTree import fromstring
import requests
from memoized import Memoized

API_URL = 'http://tools.google.com/service/update2'

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_STATIC = os.path.join(APP_ROOT, 'static')

with open(os.path.join(APP_STATIC, 'post_data_stable.xml')) as f:
    POST_DATA_STABLE = f.read().replace('\n', '')

with open(os.path.join(APP_STATIC, 'post_data_beta.xml')) as f:
    POST_DATA_BETA = f.read().replace('\n', '')

with open(os.path.join(APP_STATIC, 'post_data_dev.xml')) as f:
    POST_DATA_DEV = f.read().replace('\n', '')

post_data = OrderedDict([('stable', POST_DATA_STABLE),
                         ('beta', POST_DATA_BETA),
                         ('dev', POST_DATA_DEV)])


@Memoized
def get_response(channel):
    r = requests.post(API_URL, data=post_data[channel])
    root = fromstring(r.text)
    package = root.find('app/updatecheck/manifest/packages/package').attrib['name']
    return [i.attrib['codebase'] + package for i in root.findall('app/updatecheck/urls/url')]


def get_links(channel):
    result = OrderedDict()
    if channel not in post_data and channel != 'all':
        return None
    for k, v in post_data.iteritems():
        if k == channel or channel == 'all':
            result[k] = get_response(k)
    return result


if __name__ == '__main__':
    if len(sys.argv) == 2:
        links = get_links(sys.argv[1])
    else:
        links = get_links('stable')
    if not links:
        print 'not get'
        sys.exit(-1)
    for link in links.iteritems():
        print link
