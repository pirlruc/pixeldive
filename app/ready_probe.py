"""Loopback ``/ready`` probe for Docker HEALTHCHECK (HTTP or HTTPS)."""

from __future__ import annotations

import http.client
import os
import ssl
import sys

_TRUE = frozenset({"1", "true", "yes", "on"})


def main() -> None:
    """Exit 0 when ``/ready`` succeeds; exit 1 on connection or HTTP errors."""
    try:
        probe()
    except OSError:
        sys.exit(1)


def probe() -> None:
    """GET ``/ready`` on the loopback HTTP or HTTPS port."""
    port = int(os.environ.get("HTTP_PORT", "8000"))
    if env_flag("HTTP_INSECURE", default=True):
        get_ready(http.client.HTTPConnection("127.0.0.1", port, timeout=4))
        return
    get_ready(
        http.client.HTTPSConnection(
            "127.0.0.1",
            port,
            timeout=4,
            context=https_context(),
        ),
    )


def get_ready(conn: http.client.HTTPConnection) -> None:
    """Issue GET /ready and raise OSError on a non-success status."""
    try:
        conn.request("GET", "/ready")
        response = conn.getresponse()
        if response.status >= 400:
            msg = f"ready {response.status}"
            raise OSError(msg)
    finally:
        conn.close()


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
