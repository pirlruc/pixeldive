"""gRPC bearer auth (SEC-001)."""

from __future__ import annotations

from pathlib import Path

import grpc
import pytest

from app.config import Settings
from app.database import create_engine, init_db, session_factory
from app.grpc_server import start_grpc_server
from app.pb import session_service_pb2 as pb
from app.pb import session_service_pb2_grpc as pb_grpc
from app.service import SessionService
from app.storage import LocalFilesystemStorage
from tests.test_grpc import _create_request


@pytest.mark.asyncio
async def test_grpc_unauthenticated_and_forbidden(tmp_path: Path) -> None:
    """Missing metadata is UNAUTHENTICATED; the other tenant is NOT_FOUND."""
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'grpc-auth.db'}",
        storage_backend="local",
        storage_root=tmp_path / "images",
        auth_required=True,
        api_keys="alpha:tenant-a,beta:tenant-b",
        grpc_insecure=True,
        log_json=False,
    )
    engine = create_engine(settings)
    await init_db(engine)
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    service = SessionService(
        session_factory(engine),
        LocalFilesystemStorage(settings.storage_root),
        settings,
    )
    server, port = await start_grpc_server(service, "127.0.0.1", 0)
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    stub = pb_grpc.SessionServiceStub(channel)
    try:
        with pytest.raises(grpc.aio.AioRpcError) as missing:
            await stub.CreateSession(_create_request())
        assert missing.value.code() == grpc.StatusCode.UNAUTHENTICATED
        created = await stub.CreateSession(
            _create_request(),
            metadata=(("authorization", "Bearer alpha"),),
        )
        session_id = created.session.id
        with pytest.raises(grpc.aio.AioRpcError) as denied:
            await stub.GetSession(
                pb.GetSessionRequest(session_id=session_id),
                metadata=(("authorization", "Bearer beta"),),
            )
        assert denied.value.code() == grpc.StatusCode.NOT_FOUND
    finally:
        await channel.close()
        await server.stop(grace=0)
        await engine.dispose()
