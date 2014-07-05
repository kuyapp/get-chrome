#!/usr/bin/env python
# -*- coding:utf-8 -*-

import time
from flask import Flask
from flask import render_template, redirect
from get_links import get_links

app = Flask(__name__)

current_milli_time = lambda: int(round(time.time() * 1000)) % 10000


@app.route('/')
@app.route('/channel/')
@app.route('/channel/<channel>')
def show_link(channel='stable'):
    start_time = current_milli_time()
    links = get_links(channel)
    end_time = current_milli_time()
    print 'cost {time}'.format(time=end_time-start_time)
    if links is None:
        return redirect('/channel/stable')
    return render_template('index.html', links=links)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
