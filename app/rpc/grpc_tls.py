"""gRPC TLS credential construction (SEC-001, SEC-007)."""

from __future__ import annotations

import grpc

from app.config import Settings
from app.tls_files import grpc_tls_files


def build_grpc_server_credentials(settings: Settings) -> grpc.ServerCredentials | None:
    """Return TLS credentials, or None when insecure bind is explicitly allowed.

    Args:
        settings: TLS file paths and the insecure-bind flag.

    Returns:
        grpc.ServerCredentials | None: Server credentials when cert and key
        resolve; otherwise None.
    """
    files = grpc_tls_files(settings)
    if files is None:
        return None
    client_ca = files.client_ca_file.read_bytes() if files.client_ca_file is not None else None
    return grpc.ssl_server_credentials(
        [(files.key_file.read_bytes(), files.cert_file.read_bytes())],
        root_certificates=client_ca,
        require_client_auth=client_ca is not None,
    )
