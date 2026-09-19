"""gRPC TLS credential construction (SEC-001)."""

from __future__ import annotations

import grpc

from app.config import Settings


def build_grpc_server_credentials(settings: Settings) -> grpc.ServerCredentials | None:
    """Return TLS credentials, or None when insecure bind is explicitly allowed.

    Raises:
        RuntimeError: production-style bind requested without cert/key files.
    """
    cert = settings.grpc_tls_cert_file
    key = settings.grpc_tls_key_file
    if cert is not None and key is not None:
        client_ca = (
            settings.grpc_tls_client_ca_file.read_bytes()
            if settings.grpc_tls_client_ca_file is not None
            else None
        )
        return grpc.ssl_server_credentials(
            [(key.read_bytes(), cert.read_bytes())],
            root_certificates=client_ca,
            require_client_auth=client_ca is not None,
        )
    if settings.grpc_insecure:
        return None
    msg = "GRPC_INSECURE is false but GRPC_TLS_CERT_FILE / GRPC_TLS_KEY_FILE are unset"
    raise RuntimeError(msg)
