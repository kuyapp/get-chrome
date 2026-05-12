"""Application factory for the Chrome installer URL service."""

from .config import Config
from .web import create_app

__all__ = ["Config", "create_app"]
