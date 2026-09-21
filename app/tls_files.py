"""Shared PEM path resolution for HTTP and gRPC TLS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings


@dataclass(frozen=True, slots=True)
class TlsFiles:
    """Resolved certificate, key, and optional client-CA paths."""

    cert_file: Path
    key_file: Path
    client_ca_file: Path | None


def resolve_tls_files(
    *,
    insecure: bool,
    cert_file: Path | None,
    key_file: Path | None,
    client_ca_file: Path | None,
    shared_cert: Path | None,
    shared_key: Path | None,
    shared_ca: Path | None,
    required_error: str,
) -> TlsFiles | None:
    """Return PEM paths, falling back to the shared pair, or None if insecure.

    Args:
        insecure: When True, missing cert/key files are allowed.
        cert_file: Transport-specific certificate path.
        key_file: Transport-specific private key path.
        client_ca_file: Transport-specific client CA for mTLS.
        shared_cert: Fallback certificate used by both transports.
        shared_key: Fallback private key used by both transports.
        shared_ca: Fallback client CA used by both transports.
        required_error: Raised when TLS is required but files are incomplete.

    Returns:
        TlsFiles | None: Resolved paths, or None when plaintext is allowed.

    Raises:
        RuntimeError: TLS is required and cert/key are unset.
    """
    cert = cert_file or shared_cert
    key = key_file or shared_key
    ca = client_ca_file or shared_ca
    if cert is not None and key is not None:
        return TlsFiles(cert, key, ca)
    if insecure:
        return None
    raise RuntimeError(required_error)


def http_tls_files(settings: Settings) -> TlsFiles | None:
    """Resolve HTTP TLS files (per-transport, then shared ``TLS_*``)."""
    return resolve_tls_files(
        insecure=settings.http_insecure,
        cert_file=settings.http_tls_cert_file,
        key_file=settings.http_tls_key_file,
        client_ca_file=settings.http_tls_client_ca_file,
        shared_cert=settings.tls_cert_file,
        shared_key=settings.tls_key_file,
        shared_ca=settings.tls_client_ca_file,
        required_error="HTTP_INSECURE is false but TLS cert/key files are unset",
    )


def grpc_tls_files(settings: Settings) -> TlsFiles | None:
    """Resolve gRPC TLS files (per-transport, then shared ``TLS_*``)."""
    return resolve_tls_files(
        insecure=settings.grpc_insecure,
        cert_file=settings.grpc_tls_cert_file,
        key_file=settings.grpc_tls_key_file,
        client_ca_file=settings.grpc_tls_client_ca_file,
        shared_cert=settings.tls_cert_file,
        shared_key=settings.tls_key_file,
        shared_ca=settings.tls_client_ca_file,
        required_error="GRPC_INSECURE is false but TLS cert/key files are unset",
    )
