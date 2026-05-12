#!/usr/bin/env python3
"""WSGI entrypoint for the Chrome installer URL service."""

from get_chrome import Config, create_app

app = create_app()


if __name__ == "__main__":
    config: Config = app.config["APP_CONFIG"]
    app.run(host="0.0.0.0", port=config.port, debug=True)
