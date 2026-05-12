Get Chrome Installer
====================

A small Flask app that returns current Google Chrome installer URLs for Windows
stable, beta, and dev channels.

The app posts the Google Update request payloads in `static/post_data_*.xml` to
Google Update, parses the response, and renders the returned installer URLs.
Responses are cached in memory for 60 seconds by default.

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
