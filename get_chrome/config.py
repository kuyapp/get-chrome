"""Runtime configuration for the Chrome installer URL service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    """Typed app configuration loaded from environment variables."""

    google_update_url: str = "https://tools.google.com/service/update2"
    cache_ttl_seconds: int = 60
    url_timeout_seconds: int = 20
    port: int = 5000
    payload_dir: Path = PROJECT_ROOT / "static"
    template_dir: Path = PROJECT_ROOT / "templates"
    static_dir: Path = PROJECT_ROOT / "static"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Config":
        values = os.environ if env is None else env
        return cls(
            google_update_url=values.get("GOOGLE_UPDATE_URL", cls.google_update_url),
            cache_ttl_seconds=_read_positive_int(values, "CACHE_TTL_SECONDS", cls.cache_ttl_seconds),
            url_timeout_seconds=_read_positive_int(values, "URL_TIMEOUT_SECONDS", cls.url_timeout_seconds),
            port=_read_positive_int(values, "PORT", cls.port),
        )


def _read_positive_int(values: Mapping[str, str], key: str, default: int) -> int:
    raw_value = values.get(key)
    if raw_value is None:
        return default

    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer") from exc

    if parsed <= 0:
        raise ValueError(f"{key} must be greater than zero")
    return parsed
