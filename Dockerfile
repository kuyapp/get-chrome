FROM python:2-alpine

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN apk --update add libmemcached-dev

COPY requirements.txt /usr/src/app/

RUN apk --update add  --virtual build-dependencies build-base zlib-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del build-dependencies

COPY . /usr/src/app
