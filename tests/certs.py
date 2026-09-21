"""Generate short-lived localhost PEMs for TLS handshake tests."""

from __future__ import annotations

import subprocess
from pathlib import Path


def write_self_signed(directory: Path) -> tuple[Path, Path]:
    """Write a 1-day self-signed cert for localhost and 127.0.0.1."""
    cert = directory / "server.crt"
    key = directory / "server.key"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ],
        check=True,
        capture_output=True,
    )
    return cert, key
