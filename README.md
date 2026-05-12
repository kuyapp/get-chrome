Get Chrome Installer
====================

A small Cloudflare Workers service that returns current Google Chrome installer
URLs for Windows stable, beta, and dev channels.

The Worker posts embedded Google Update request payloads to Google Update,
parses the XML response, and renders the returned installer URLs. Responses are
cached in the Worker isolate memory for 60 seconds by default.

Architecture and technology choices
-----------------------------------

This project is now deployed as a TypeScript Cloudflare Worker:

* **Worker HTTP adapter** (`src/index.ts`) owns routing, redirects, rendering,
  Google Update requests, XML response parsing, and in-memory caching.
* **Wrangler configuration** (`wrangler.toml`) points Cloudflare Workers at the
  TypeScript entrypoint and defines default environment variables.
* The historical Python modules under `get_chrome/` remain in the repository as
  reference material for the original Flask implementation, but the Python
  deployment entry files have been removed.

Endpoints
---------

* `/`, `/channel/`, or `/channel/stable` - stable channel installer URLs
* `/channel/beta` - beta channel installer URLs
* `/channel/dev` - dev channel installer URLs
* `/channel/all` - stable, beta, and dev installer URLs
* Any unsupported `/channel/*` path redirects to `/channel/stable`

Configuration
-------------

Wrangler variables in `wrangler.toml`:

* `GOOGLE_UPDATE_URL` - Google Update endpoint. Defaults to
  `https://tools.google.com/service/update2`.
* `CACHE_TTL_SECONDS` - Worker isolate memory cache TTL. Defaults to `60`.
* `URL_TIMEOUT_SECONDS` - outbound Google Update request timeout. Defaults to
  `20`.

Run locally
-----------

```bash
npm install
npm run dev
```

Deploy
------

```bash
npm run deploy
```

Test
----

```bash
npm run typecheck
```
