"""Shared stub host used by gRPC SDK mixins."""

from __future__ import annotations

from typing import Any

from app.pb import session_service_pb2_grpc as pb_grpc


class GrpcHostMixin:
    """``connect`` / metadata / stub surface implemented by ``GrpcClient``."""

    async def connect(self) -> None:
        """Open the channel; implemented by GrpcClient."""
        raise NotImplementedError  # pragma: no cover

    def _metadata(self) -> list[tuple[str, str]]:
        """Invocation metadata; implemented by GrpcClient."""
        raise NotImplementedError  # pragma: no cover

    def _require_stub(self) -> pb_grpc.SessionServiceStub:
        """Return the stub; implemented by GrpcClient."""
        raise NotImplementedError  # pragma: no cover

    async def _unary(self, rpc: str, request: object) -> Any:
        """Call a unary RPC after ensuring the channel is open."""
        await self.connect()
        method = getattr(self._require_stub(), rpc)
        return await method(request, metadata=self._metadata())
