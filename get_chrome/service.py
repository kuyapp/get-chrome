"""Application service that coordinates payloads, Google Update, and caching."""

from __future__ import annotations

from collections import OrderedDict

from .cache import TTLCache
from .channels import ALL_CHANNELS, SUPPORTED_CHANNELS, is_supported_selection
from .google_update import GoogleUpdateClient, parse_installer_urls


class ChromeInstallerService:
    """Use case layer for resolving Chrome installer URLs by channel."""

    def __init__(
        self,
        client: GoogleUpdateClient,
        payloads: "OrderedDict[str, bytes]",
        cache: TTLCache[list[str]],
    ):
        self._client = client
        self._payloads = payloads
        self._cache = cache

    def channels_for(self, selected_channel: str) -> tuple[str, ...]:
        """Return channels to render for a supported selection."""
        if not is_supported_selection(selected_channel):
            return ()
        if selected_channel == ALL_CHANNELS:
            return SUPPORTED_CHANNELS
        return (selected_channel,)

    def installer_urls(self, channel: str) -> list[str]:
        """Return installer URLs for one concrete channel."""
        cached_urls = self._cache.get(channel)
        if cached_urls is not None:
            return list(cached_urls)

        xml_body = self._client.fetch(self._payloads[channel])
        urls = parse_installer_urls(xml_body)
        self._cache.set(channel, urls)
        return urls

    def installer_urls_for(self, selected_channel: str) -> "OrderedDict[str, list[str]]":
        """Return ordered installer URLs for a channel selection."""
        links: "OrderedDict[str, list[str]]" = OrderedDict()
        for channel in self.channels_for(selected_channel):
            links[channel] = self.installer_urls(channel)
        return links
