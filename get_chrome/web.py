"""Flask wiring for the Chrome installer URL service."""

from __future__ import annotations

from flask import Flask, current_app, redirect, render_template

from .cache import TTLCache
from .config import Config
from .google_update import ChromeUpdateError, GoogleUpdateClient, load_channel_payloads
from .service import ChromeInstallerService


def create_app(config: Config | None = None, service: ChromeInstallerService | None = None) -> Flask:
    """Create and configure the Flask application."""
    resolved_config = config or Config.from_env()
    app = Flask(
        __name__,
        template_folder=str(resolved_config.template_dir),
        static_folder=str(resolved_config.static_dir),
    )
    app.config["APP_CONFIG"] = resolved_config
    app.config["INSTALLER_SERVICE"] = service or _build_service(resolved_config)

    @app.route("/")
    @app.route("/channel/")
    @app.route("/channel/<channel>")
    def show_link(channel: str = "stable"):
        installer_service: ChromeInstallerService = current_app.config["INSTALLER_SERVICE"]
        links = installer_service.installer_urls_for(channel)
        if not links:
            return redirect("/channel/stable")
        return render_template("index.html", links=links)

    @app.errorhandler(ChromeUpdateError)
    def handle_chrome_update_error(error: ChromeUpdateError):
        return render_template("error.html", error=error), 502

    return app


def _build_service(config: Config) -> ChromeInstallerService:
    payloads = load_channel_payloads(config.payload_dir)
    client = GoogleUpdateClient(config.google_update_url, config.url_timeout_seconds)
    cache: TTLCache[list[str]] = TTLCache(config.cache_ttl_seconds)
    return ChromeInstallerService(client, payloads, cache)
