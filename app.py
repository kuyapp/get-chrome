#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small Flask app that returns current Chrome installer URLs.

The app talks to Google Update using the request payloads in ``static/`` and
renders the installer URLs for the stable, beta, dev, or all channels.
"""

from __future__ import annotations

import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from flask import Flask, redirect, render_template

API_URL = os.environ.get("GOOGLE_UPDATE_URL", "https://tools.google.com/service/update2")
APP_ROOT = Path(__file__).resolve().parent
APP_STATIC = APP_ROOT / "static"
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "60"))
URL_TIMEOUT_SECONDS = int(os.environ.get("URL_TIMEOUT_SECONDS", "20"))
CHANNELS = ("stable", "beta", "dev")

app = Flask(__name__)


def load_post_data() -> "OrderedDict[str, bytes]":
    """Load Google Update request payloads for each supported channel."""
    payloads: "OrderedDict[str, bytes]" = OrderedDict()
    for channel in CHANNELS:
        payload = (APP_STATIC / f"post_data_{channel}.xml").read_text(encoding="utf-8")
        payloads[channel] = payload.replace("\n", "").encode("utf-8")
    return payloads


post_data = load_post_data()


@dataclass
class CacheEntry:
    expires_at: float
    value: list[str]


class TTLCache:
    """Tiny in-process TTL cache for channel responses."""

    def __init__(self, time_func: Callable[[], float] = time.time):
        self._entries: dict[str, CacheEntry] = {}
        self._time = time_func

    def get(self, key: str) -> list[str] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._time():
            self._entries.pop(key, None)
            return None
        return list(entry.value)

    def set(self, key: str, value: list[str], timeout: int = CACHE_TTL_SECONDS) -> None:
        self._entries[key] = CacheEntry(self._time() + timeout, list(value))

    def clear(self) -> None:
        self._entries.clear()


cache = TTLCache()


class ChromeUpdateError(RuntimeError):
    """Raised when Google Update does not return installer metadata."""


def parse_installer_urls(xml_body: bytes) -> list[str]:
    """Parse Google Update XML and return full installer URLs."""
    root = ElementTree.fromstring(xml_body)
    package = root.find("app/updatecheck/manifest/packages/package")
    urls = root.findall("app/updatecheck/urls/url")

    if package is None or "name" not in package.attrib or not urls:
        status = root.find("app/updatecheck")
        status_text = status.attrib.get("status", "unknown") if status is not None else "unknown"
        raise ChromeUpdateError(f"Google Update response did not include installer URLs: {status_text}")

    package_name = package.attrib["name"]
    return [url.attrib["codebase"] + package_name for url in urls if "codebase" in url.attrib]


def fetch_installer_urls(channel: str) -> list[str]:
    """Fetch installer URLs for a channel from Google Update."""
    request = Request(
        API_URL,
        data=post_data[channel],
        headers={"Content-Type": "text/xml; charset=UTF-8"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=URL_TIMEOUT_SECONDS) as response:
            return parse_installer_urls(response.read())
    except (HTTPError, URLError, TimeoutError, ElementTree.ParseError) as exc:
        raise ChromeUpdateError(f"Unable to fetch Chrome installer URLs for {channel}") from exc


def get_response(channel: str) -> list[str]:
    cached_value = cache.get(channel)
    if cached_value is not None:
        app.logger.debug("cache hit: %s", channel)
        return cached_value

    app.logger.debug("cache miss: %s", channel)
    urls = fetch_installer_urls(channel)
    cache.set(channel, urls)
    return urls


@app.route("/")
@app.route("/channel/")
@app.route("/channel/<channel>")
def show_link(channel: str = "stable"):
    if channel not in (*CHANNELS, "all"):
        return redirect("/channel/stable")

    links = OrderedDict()
    for key in CHANNELS:
        if channel in (key, "all"):
            links[key] = get_response(key)
    return render_template("index.html", links=links)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
