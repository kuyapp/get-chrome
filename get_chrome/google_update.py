"""Google Update client and response parser."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .channels import SUPPORTED_CHANNELS


class ChromeUpdateError(RuntimeError):
    """Raised when Google Update cannot provide installer metadata."""


class HttpResponse(Protocol):
    def __enter__(self) -> "HttpResponse": ...
    def __exit__(self, exc_type, exc, traceback) -> bool | None: ...
    def read(self) -> bytes: ...


HttpOpener = Callable[..., HttpResponse]


class GoogleUpdateClient:
    """HTTP client for the Google Update service."""

    def __init__(self, endpoint: str, timeout_seconds: int, opener: HttpOpener = urlopen):
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._opener = opener

    def fetch(self, payload: bytes) -> bytes:
        request = Request(
            self._endpoint,
            data=payload,
            headers={"Content-Type": "text/xml; charset=UTF-8"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise ChromeUpdateError("Unable to fetch Chrome installer metadata") from exc


def load_channel_payloads(payload_dir: Path) -> "OrderedDict[str, bytes]":
    """Load request XML payloads for every supported channel."""
    payloads: "OrderedDict[str, bytes]" = OrderedDict()
    for channel in SUPPORTED_CHANNELS:
        path = payload_dir / f"post_data_{channel}.xml"
        payloads[channel] = path.read_text(encoding="utf-8").replace("\n", "").encode("utf-8")
    return payloads


def parse_installer_urls(xml_body: bytes) -> list[str]:
    """Extract full installer URLs from a Google Update XML response."""
    try:
        root = ElementTree.fromstring(xml_body)
    except ElementTree.ParseError as exc:
        raise ChromeUpdateError("Google Update returned invalid XML") from exc

    package = root.find("app/updatecheck/manifest/packages/package")
    url_nodes = root.findall("app/updatecheck/urls/url")

    if package is None or "name" not in package.attrib:
        raise _missing_metadata_error(root)

    package_name = package.attrib["name"]
    installer_urls = [node.attrib["codebase"] + package_name for node in url_nodes if "codebase" in node.attrib]
    if not installer_urls:
        raise _missing_metadata_error(root)
    return installer_urls


def _missing_metadata_error(root: ElementTree.Element) -> ChromeUpdateError:
    updatecheck = root.find("app/updatecheck")
    status = updatecheck.attrib.get("status", "unknown") if updatecheck is not None else "unknown"
    return ChromeUpdateError(f"Google Update response did not include installer URLs: {status}")
