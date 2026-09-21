"""HTTP TLS context and uvicorn server construction (SEC-007)."""

from __future__ import annotations

import ssl
from collections.abc import Callable
from functools import partial
from typing import Any

import uvicorn

from app.config import Settings
from app.tls_files import TlsFiles, http_tls_files


def build_http_ssl_context(settings: Settings) -> ssl.SSLContext | None:
    """Return a TLS server context, or None when HTTP plaintext is allowed.

    Args:
        settings: HTTP/TLS file paths and the insecure-bind flag.

    Returns:
        ssl.SSLContext | None: Server context when cert and key resolve;
        otherwise None.
    """
    files = http_tls_files(settings)
    if files is None:
        return None
    return ssl_context_for(files)


def ssl_context_for(files: TlsFiles) -> ssl.SSLContext:
    """Build a TLS 1.2+ server context from resolved PEM paths."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(str(files.cert_file), str(files.key_file))
    if files.client_ca_file is not None:
        ctx.load_verify_locations(str(files.client_ca_file))
        ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.set_alpn_protocols(["http/1.1"])
    return ctx


def uvicorn_ssl_context(
    _config: uvicorn.Config,
    _default_factory: Callable[[], ssl.SSLContext],
    files: TlsFiles,
) -> ssl.SSLContext:
    """Ignore uvicorn's certfile factory; load TLS 1.2+ from resolved PEMs."""
    del _config, _default_factory
    return ssl_context_for(files)


def build_http_server(app: Any, settings: Settings) -> uvicorn.Server:
    """Bind uvicorn to ``settings`` with TLS when HTTP_INSECURE is false."""
    files = http_tls_files(settings)
    kwargs: dict[str, Any] = {
        "app": app,
        "host": settings.http_host,
        "port": settings.http_port,
        "log_level": "info",
        "lifespan": "on",
    }
    if files is not None:
        kwargs["ssl_context_factory"] = partial(uvicorn_ssl_context, files=files)
    return uvicorn.Server(uvicorn.Config(**kwargs))
