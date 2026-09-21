"""HTTP and gRPC TLS construction and handshake (SEC-007)."""

from __future__ import annotations

import asyncio
import socket
import ssl
from pathlib import Path

import grpc
import httpx
import pytest
import uvicorn
from pixeldive_sdk import GrpcClient, RestClient, sample_session_payload

from app.api import create_app
from app.config import Settings
from app.grpc_server import start_grpc_server
from app.http_tls import build_http_server, build_http_ssl_context
from app.pb import session_service_pb2 as pb
from app.pb import session_service_pb2_grpc as pb_grpc
from app.ready_probe import env_flag, first_env, https_context, probe
from app.runtime import validate_auth_settings
from app.tls_files import grpc_tls_files, http_tls_files
from tests.certs import write_self_signed
from tests.conftest import PNG_1X1
from tests.factories import auth_settings, make_service


def unused_port() -> int:
    """Bind an ephemeral loopback port and release it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_empty_tls_env_paths_are_unset() -> None:
    """Compose interpolates empty strings; those must not become Path('')."""
    settings = Settings(tls_cert_file="", http_tls_key_file="", grpc_tls_client_ca_file="")
    assert settings.tls_cert_file is None
    assert settings.http_tls_key_file is None
    assert settings.grpc_tls_client_ca_file is None


def test_shared_tls_files_serve_both_transports(tmp_path: Path) -> None:
    """TLS_CERT_FILE / TLS_KEY_FILE fill in when per-transport paths are unset."""
    cert, key = write_self_signed(tmp_path)
    settings = Settings(
        http_insecure=False,
        grpc_insecure=False,
        tls_cert_file=cert,
        tls_key_file=key,
        tls_client_ca_file=cert,
    )
    http_files = http_tls_files(settings)
    grpc_files = grpc_tls_files(settings)
    assert http_files is not None and grpc_files is not None
    assert http_files.cert_file == cert
    assert grpc_files.key_file == key
    assert http_files.client_ca_file == cert
    ctx = build_http_ssl_context(settings)
    assert ctx is not None
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_http_tls_requires_files_when_secure() -> None:
    """HTTP_INSECURE=false without PEMs fails closed."""
    assert build_http_ssl_context(Settings(http_insecure=True)) is None
    with pytest.raises(RuntimeError, match="HTTP_INSECURE"):
        build_http_ssl_context(Settings(http_insecure=False))


def test_production_requires_http_and_grpc_tls() -> None:
    """ENVIRONMENT=production refuses plaintext HTTP or gRPC."""
    with pytest.raises(RuntimeError, match="HTTP_INSECURE"):
        validate_auth_settings(
            Settings(
                environment="prod",
                auth_required=True,
                api_keys="alpha:tenant-a",
                http_insecure=True,
                grpc_insecure=False,
            ),
        )
    with pytest.raises(RuntimeError, match="GRPC_INSECURE"):
        validate_auth_settings(
            Settings(
                environment="prod",
                auth_required=True,
                api_keys="alpha:tenant-a",
                http_insecure=False,
                grpc_insecure=True,
            ),
        )


def test_ready_probe_helpers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Loopback HTTPS context loads the first configured server cert."""
    cert, _key = write_self_signed(tmp_path)
    monkeypatch.delenv("HTTP_INSECURE", raising=False)
    assert env_flag("HTTP_INSECURE", default=True) is True
    monkeypatch.setenv("HTTP_INSECURE", "false")
    assert env_flag("HTTP_INSECURE", default=True) is False
    monkeypatch.setenv("HTTP_TLS_CERT_FILE", str(cert))
    ctx = https_context()
    assert ctx.check_hostname is False
    monkeypatch.setenv("HTTP_TLS_CERT_FILE", "")
    monkeypatch.setenv("TLS_CERT_FILE", str(cert))
    assert first_env("HTTP_TLS_CERT_FILE", "TLS_CERT_FILE") == str(cert)


async def _wait_http(server: uvicorn.Server) -> None:
    """Wait until uvicorn has bound its sockets."""
    for _ in range(100):
        if server.started:
            return
        await asyncio.sleep(0.05)
    msg = "HTTP server did not start"
    raise RuntimeError(msg)


@pytest.mark.asyncio
async def test_https_and_grpcs_round_trip(tmp_path: Path) -> None:
    """Bearer auth over HTTPS and TLS gRPC with a shared self-signed PEM."""
    cert, key = write_self_signed(tmp_path)
    http_port = unused_port()
    settings = auth_settings(
        tmp_path,
        http_insecure=False,
        grpc_insecure=False,
        tls_cert_file=cert,
        tls_key_file=key,
        http_host="127.0.0.1",
        http_port=http_port,
    )
    service, engine = await make_service(settings)
    app = create_app(service)
    http = build_http_server(app, settings)
    grpc_server, grpc_port = await start_grpc_server(service, "127.0.0.1", 0)
    task = asyncio.create_task(http.serve())
    try:
        await _wait_http(http)
        ca = str(cert)
        async with RestClient(
            f"https://127.0.0.1:{http_port}",
            token="alpha",
            verify=ca,
        ) as client:
            health = await client.health()
            assert health["status"] == "ok"
            created = await client.create_session(sample_session_payload("tls-http"))
            uploaded = await client.upload_image(
                created["id"],
                "frame.png",
                PNG_1X1,
                "image/png",
            )
            assert uploaded["size_bytes"] == len(PNG_1X1)
        pem = cert.read_bytes()
        async with GrpcClient(
            f"localhost:{grpc_port}",
            token="alpha",
            insecure=False,
            root_certificates=pem,
        ) as grpc_client:
            session = await grpc_client.create_session(sample_session_payload("tls-grpc"))
            assert session.session_name == "tls-grpc"
        channel = grpc.aio.secure_channel(
            f"localhost:{grpc_port}",
            grpc.ssl_channel_credentials(root_certificates=pem),
            options=[("grpc.ssl_target_name_override", "localhost")],
        )
        stub = pb_grpc.SessionServiceStub(channel)
        listed = await stub.ListSessions(
            pb.ListSessionsRequest(limit=10),
            metadata=(("authorization", "Bearer alpha"),),
        )
        assert listed.sessions
        await channel.close()
    finally:
        http.should_exit = True
        await task
        await grpc_server.stop(grace=0)
        await engine.dispose()


@pytest.mark.asyncio
async def test_https_rejects_missing_bearer(tmp_path: Path) -> None:
    """TLS does not replace application auth: missing tokens are still 401."""
    cert, key = write_self_signed(tmp_path)
    http_port = unused_port()
    settings = auth_settings(
        tmp_path,
        http_insecure=False,
        tls_cert_file=cert,
        tls_key_file=key,
        http_host="127.0.0.1",
        http_port=http_port,
    )
    service, engine = await make_service(settings)
    http = build_http_server(create_app(service), settings)
    task = asyncio.create_task(http.serve())
    try:
        await _wait_http(http)
        async with httpx.AsyncClient(verify=str(cert)) as client:
            response = await client.post(
                f"https://127.0.0.1:{http_port}/api/v1/sessions",
                json=sample_session_payload("no-token"),
            )
        assert response.status_code == 401
    finally:
        http.should_exit = True
        await task
        await engine.dispose()


def test_ready_probe_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plaintext probe uses HTTP when HTTP_INSECURE is true."""
    calls: list[str] = []

    def fake_open(url: str, timeout: object = None, context: object = None) -> object:
        del timeout, context
        calls.append(url)
        return object()

    monkeypatch.setattr("app.ready_probe.urllib.request.urlopen", fake_open)
    monkeypatch.setenv("HTTP_INSECURE", "true")
    monkeypatch.setenv("HTTP_PORT", "8000")
    probe()
    assert calls == ["http://127.0.0.1:8000/ready"]
    monkeypatch.setenv("HTTP_INSECURE", "false")
    probe()
    assert calls[-1] == "https://127.0.0.1:8000/ready"


def test_ready_probe_main_exits_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """HEALTHCHECK process exits 1 when the probe cannot connect."""
    from app.ready_probe import main

    monkeypatch.setattr(
        "app.ready_probe.probe",
        lambda: (_ for _ in ()).throw(OSError("down")),
    )
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 1
