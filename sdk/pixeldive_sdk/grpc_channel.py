"""Open an aio gRPC channel for the Python SDK."""

from __future__ import annotations

import grpc

from app.pb import session_service_pb2_grpc as pb_grpc
from pixeldive_sdk.grpc_options import CHANNEL_OPTIONS


def open_channel(
    target: str,
    *,
    insecure: bool,
    root_certificates: bytes | None = None,
    private_key: bytes | None = None,
    certificate_chain: bytes | None = None,
) -> grpc.aio.Channel:
    """Create an insecure or TLS channel to ``target``.

    Args:
        target: ``host:port`` for the session service.
        insecure: When True, skip TLS (local/dev only).
        root_certificates: PEM CA bundle used to verify the server.
        private_key: Optional client key PEM for mTLS.
        certificate_chain: Optional client cert PEM for mTLS.

    Returns:
        grpc.aio.Channel: An aio channel using CHANNEL_OPTIONS.
    """
    if insecure:
        return grpc.aio.insecure_channel(target, options=CHANNEL_OPTIONS)
    credentials = grpc.ssl_channel_credentials(
        root_certificates=root_certificates,
        private_key=private_key,
        certificate_chain=certificate_chain,
    )
    return grpc.aio.secure_channel(target, credentials, options=CHANNEL_OPTIONS)


def stub_for(channel: grpc.aio.Channel) -> pb_grpc.SessionServiceStub:
    """Bind the generated SessionService stub to ``channel``."""
    return pb_grpc.SessionServiceStub(channel)
