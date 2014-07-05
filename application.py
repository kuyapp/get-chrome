#!/usr/bin/env python
# -*- coding:utf-8 -*-

from flask import Flask
from flask import render_template, redirect
from get_links import get_links

app = Flask(__name__)


@app.route('/')
@app.route('/channel/')
@app.route('/channel/<channel>')
def show_link(channel='stable'):
    links = get_links(channel)
    if links is None:
        return redirect('/channel/stable')
    return render_template('index.html', links=links)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
