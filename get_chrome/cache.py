"""Cache primitives used by the application service layer."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class CacheEntry(Generic[T]):
    expires_at: float
    value: T


class TTLCache(Generic[T]):
    """Small in-process TTL cache.

    The app only caches a few channel lookups, so a process-local cache avoids
    an external memcached dependency while keeping the service easy to deploy.
    """

    def __init__(self, ttl_seconds: int, time_func: Callable[[], float] = time.time):
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry[T]] = {}
        self._time = time_func

    def get(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._time():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._entries[key] = CacheEntry(self._time() + self._ttl_seconds, value)

    def clear(self) -> None:
        self._entries.clear()
