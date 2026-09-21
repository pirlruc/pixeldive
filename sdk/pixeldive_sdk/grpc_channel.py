"""Open an aio gRPC channel for the Python SDK."""

from __future__ import annotations

import grpc

from app.pb import session_service_pb2_grpc as pb_grpc
from pixeldive_sdk.grpc_options import CHANNEL_OPTIONS

ChannelOption = tuple[str, int | str]


def open_channel(
    target: str,
    *,
    insecure: bool,
    root_certificates: bytes | None = None,
    private_key: bytes | None = None,
    certificate_chain: bytes | None = None,
    ssl_target_name_override: str | None = None,
) -> grpc.aio.Channel:
    """Create an insecure or TLS channel to ``target``.

    Args:
        target: ``host:port`` for the session service.
        insecure: When True, skip TLS (local/dev only).
        root_certificates: PEM CA bundle used to verify the server.
        private_key: Optional client key PEM for mTLS.
        certificate_chain: Optional client cert PEM for mTLS.
        ssl_target_name_override: Optional expected TLS server name.

    Returns:
        grpc.aio.Channel: An aio channel using CHANNEL_OPTIONS.
    """
    if insecure:
        reject_tls_on_insecure(
            root_certificates,
            private_key,
            certificate_chain,
            ssl_target_name_override,
        )
        return grpc.aio.insecure_channel(target, options=CHANNEL_OPTIONS)
    credentials = grpc.ssl_channel_credentials(
        root_certificates=root_certificates,
        private_key=private_key,
        certificate_chain=certificate_chain,
    )
    return grpc.aio.secure_channel(
        target,
        credentials,
        options=channel_options(ssl_target_name_override),
    )


def reject_tls_on_insecure(*values: object) -> None:
    """Raise when TLS PEMs or a name override are mixed with insecure=True."""
    if any(value not in (None, "") for value in values):
        msg = "TLS credentials require insecure=False"
        raise ValueError(msg)


def channel_options(ssl_target_name_override: str | None) -> list[ChannelOption]:
    """CHANNEL_OPTIONS plus an optional TLS server-name override."""
    options: list[ChannelOption] = [(key, value) for key, value in CHANNEL_OPTIONS]
    if ssl_target_name_override:
        options.append(("grpc.ssl_target_name_override", ssl_target_name_override))
    return options


def stub_for(channel: grpc.aio.Channel) -> pb_grpc.SessionServiceStub:
    """Bind the generated SessionService stub to ``channel``."""
    return pb_grpc.SessionServiceStub(channel)
