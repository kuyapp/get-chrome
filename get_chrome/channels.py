"""Supported Chrome release channels."""

from __future__ import annotations

SUPPORTED_CHANNELS = ("stable", "beta", "dev")
ALL_CHANNELS = "all"


def is_supported_selection(channel: str) -> bool:
    """Return whether a requested channel or collection is supported."""
    return channel in (*SUPPORTED_CHANNELS, ALL_CHANNELS)
