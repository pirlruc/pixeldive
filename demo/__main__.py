"""Run the demo UI: ``PYTHONPATH=sdk:. python -m demo``."""

from __future__ import annotations

import os

import uvicorn

from demo.app import create_demo_app


def main() -> None:
    """Start the demo HTTP server."""
    host = os.environ.get("DEMO_HTTP_HOST", "127.0.0.1")
    port = int(os.environ.get("DEMO_HTTP_PORT", "8080"))
    uvicorn.run(create_demo_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
