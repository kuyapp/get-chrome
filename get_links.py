#!/usr/bin/env python
# -*- coding:utf-8 -*-

from lxml import etree
from lxml import objectify
import os
import sys
from collections import OrderedDict
import requests
from memoized import memoized

API_URL = 'http://tools.google.com/service/update2'

POST_DATA_DEV = '''<?xml version="1.0" encoding="UTF-8"?><request protocol="3.0" version="1.3.21.123" ismachine="0" sessionid="{12345678-1234-1234-1234-123456789012}" installsource="ondemandcheckforupdate" requestid="{12345678-1234-1234-1234-123456789012}"><os platform="win" version="6.1" sp="Service Pack 1" arch="x64" /><app appid="{4DC8B4CA-1BDA-483E-B5FA-D3C12E15B62D}" version="" nextversion="" ap="2.0-dev" lang="" brand="GGLS" client=""><updatecheck /><ping active="1" /></app></request>'''

POST_DATA_BETA = '''<?xml version="1.0" encoding="UTF-8"?><request protocol="3.0" version="1.3.21.123" ismachine="0" sessionid="{12345678-1234-1234-1234-123456789012}" installsource="ondemandcheckforupdate" requestid="{12345678-1234-1234-1234-123456789012}"><os platform="win" version="6.1" sp="Service Pack 1" arch="x64" /><app appid="{4DC8B4CA-1BDA-483E-B5FA-D3C12E15B62D}" version="" nextversion="" ap="1.1-beta" lang="" brand="GGLS" client=""><updatecheck /><ping active="1" /></app></request>'''

POST_DATA_STABLE = '''<?xml version="1.0" encoding="UTF-8"?><request protocol="3.0" version="1.3.21.123" ismachine="0" sessionid="{12345678-1234-1234-1234-123456789012}" installsource="ondemandcheckforupdate" requestid="{12345678-1234-1234-1234-123456789012}"><os platform="win" version="6.1" sp="Service Pack 1" arch="x64" /><app appid="{4DC8B4CA-1BDA-483E-B5FA-D3C12E15B62D}" version="" nextversion="" ap="-multi-chrome" lang="" brand="GGLS" client=""><updatecheck /><ping active="1" /></app></request>'''

post_data = OrderedDict([('stable', POST_DATA_STABLE),
              ('beta',   POST_DATA_BETA),
              ('dev',    POST_DATA_DEV)])


@memoized
def get_links(channel):
    print 'call with %s' % channel
    if channel not in post_data and channel != 'all':
        return None
    result = OrderedDict()
    for k, v in post_data.iteritems():
        if k == channel or channel == 'all':
            r = requests.post(API_URL, data=v)
            root = objectify.fromstring(r.text.encode('utf-8'))
            package = root.app.updatecheck.manifest.\
                packages.package.attrib.get('name')
            links = [
                i.attrib.get('codebase') + package
                for i in root.app.updatecheck.urls.url
            ]
            result[k] = links
    return result

if __name__ == '__main__':
    if len(sys.argv) == 2:
        links = get_links(sys.argv[1])
    else:
        links = get_links('stable')
    if not links:
        print 'not get'
        sys.exit(-1)
    for link in links:
        print link
