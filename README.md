Get Chrome Installer
====================

A small Flask service that returns current Google Chrome installer URLs for
Windows stable, beta, and dev channels.

The service posts the Google Update request payloads in `static/post_data_*.xml`
to Google Update, parses the XML response, and renders the returned installer
URLs. Responses are cached in memory for 60 seconds by default.

Architecture and technology choices
-----------------------------------

This project is intentionally kept small, but it is now structured as a layered
Python application instead of a single script:

* **Flask web adapter** (`get_chrome/web.py`) owns routing, rendering, redirects,
  and HTTP error responses.
* **Use-case/service layer** (`get_chrome/service.py`) coordinates channel
  selection, cache lookups, Google Update calls, and URL parsing.
* **Google Update client** (`get_chrome/google_update.py`) owns outbound HTTP,
  request payload loading, XML parsing, and provider-specific exceptions.
* **Configuration layer** (`get_chrome/config.py`) reads and validates environment
  variables into a typed `Config` object.
* **Cache layer** (`get_chrome/cache.py`) provides a tiny in-process TTL cache.

The app stays on Flask rather than moving to a heavier framework because the
feature set is a simple server-rendered page with a few routes. It uses the
Python standard library for outbound HTTP to avoid pulling in another dependency
for one POST request. The cache is process-local because only three channel
lookups are cached and the service should run without external infrastructure.

Endpoints
---------

* `/` or `/channel/stable` - stable channel installer URLs
* `/channel/beta` - beta channel installer URLs
* `/channel/dev` - dev channel installer URLs
* `/channel/all` - stable, beta, and dev installer URLs

Configuration
-------------

Environment variables:

* `GOOGLE_UPDATE_URL` - Google Update endpoint. Defaults to
  `https://tools.google.com/service/update2`.
* `CACHE_TTL_SECONDS` - in-memory cache TTL. Defaults to `60`.
* `URL_TIMEOUT_SECONDS` - outbound Google Update request timeout. Defaults to
  `20`.
* `PORT` - development server port when running `python app.py`. Defaults to
  `5000`.

Run locally
-----------

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

Run with Docker
---------------

```bash
docker build -t get-chrome .
docker run --rm -p 5000:5000 get-chrome
```

Test
----

```bash
python -m unittest
```
