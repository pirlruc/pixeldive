"""Async gRPC client for pixeldive SessionService."""

from __future__ import annotations

from typing import Self

import grpc

from app.pb import session_service_pb2_grpc as pb_grpc
from pixeldive_sdk.grpc_calls import GrpcCallsMixin
from pixeldive_sdk.grpc_channel import open_channel, stub_for


class GrpcClient(GrpcCallsMixin):
    """Thin wrapper around the generated SessionService stub."""

    def __init__(
        self,
        target: str,
        *,
        token: str | None = None,
        insecure: bool = True,
    ) -> None:
        """Connect to ``host:port`` with optional bearer metadata."""
        self._target = target
        self._token = token
        self._insecure = insecure
        self._channel: grpc.aio.Channel | None = None
        self._stub: pb_grpc.SessionServiceStub | None = None

    def _metadata(self) -> list[tuple[str, str]]:
        """Build invocation metadata including Authorization when set."""
        if not self._token:
            return []
        return [("authorization", f"Bearer {self._token}")]

    async def connect(self) -> None:
        """Open the aio channel if needed."""
        if self._channel is not None:
            return
        self._channel = open_channel(self._target, insecure=self._insecure)
        self._stub = stub_for(self._channel)

    async def aclose(self) -> None:
        """Close the channel."""
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None

    async def __aenter__(self) -> Self:
        """Connect for ``async with``."""
        await self.connect()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close on context exit."""
        await self.aclose()

    def _require_stub(self) -> pb_grpc.SessionServiceStub:
        """Return the stub or raise if connect() was not called."""
        if self._stub is None:
            msg = "GrpcClient.connect() must be called first"
            raise RuntimeError(msg)
        return self._stub
