"""Open an aio gRPC channel for the Python SDK."""

from __future__ import annotations

import grpc

from app.pb import session_service_pb2_grpc as pb_grpc
from pixeldive_sdk.grpc_options import CHANNEL_OPTIONS


def open_channel(target: str, *, insecure: bool) -> grpc.aio.Channel:
    """Create an insecure or TLS channel to ``target``."""
    if insecure:
        return grpc.aio.insecure_channel(target, options=CHANNEL_OPTIONS)
    credentials = grpc.ssl_channel_credentials()
    return grpc.aio.secure_channel(target, credentials, options=CHANNEL_OPTIONS)


def stub_for(channel: grpc.aio.Channel) -> pb_grpc.SessionServiceStub:
    """Bind the generated SessionService stub to ``channel``."""
    return pb_grpc.SessionServiceStub(channel)
