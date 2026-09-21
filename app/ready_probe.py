"""Loopback ``/ready`` probe for Docker HEALTHCHECK (HTTP or HTTPS)."""

from __future__ import annotations

import os
import ssl
import sys
import urllib.error
import urllib.request

_TRUE = frozenset({"1", "true", "yes", "on"})


def main() -> None:
    """Exit 0 when ``/ready`` succeeds; exit 1 on connection or HTTP errors."""
    try:
        probe()
    except (OSError, urllib.error.URLError):
        sys.exit(1)


def probe() -> None:
    """GET ``/ready`` on the loopback HTTP or HTTPS port."""
    port = os.environ.get("HTTP_PORT", "8000")
    if env_flag("HTTP_INSECURE", default=True):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/ready", timeout=4)
        return
    urllib.request.urlopen(
        f"https://127.0.0.1:{port}/ready",
        context=https_context(),
        timeout=4,
    )


def env_flag(name: str, *, default: bool) -> bool:
    """Parse a boolean environment flag; empty/unset uses ``default``."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in _TRUE


def https_context() -> ssl.SSLContext:
    """Trust the configured server cert; skip hostname for loopback IPs.

    Docker HEALTHCHECK always uses ``127.0.0.1``. Operators typically mint a
    cert for ``localhost``, so hostname matching would fail even when the
    signature is valid. Signature verification against the PEM remains on.
    """
    ctx = ssl.create_default_context()
    cert = first_env("HTTP_TLS_CERT_FILE", "TLS_CERT_FILE", "GRPC_TLS_CERT_FILE")
    if cert:
        ctx.load_verify_locations(cert)
    ctx.check_hostname = False
    return ctx


def first_env(*names: str) -> str:
    """Return the first non-empty environment value among ``names``."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


if __name__ == "__main__":
    main()
