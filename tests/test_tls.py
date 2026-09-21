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

from app.config import Settings
from app.pb import session_service_pb2 as pb
from app.pb import session_service_pb2_grpc as pb_grpc
from app.ready_probe import env_flag, first_env, https_context, probe
from app.rest.api import create_app
from app.rest.http_tls import build_http_server, build_http_ssl_context
from app.rpc.grpc_server import start_grpc_server
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


def test_http_server_mtls_uses_client_ca(tmp_path: Path) -> None:
    """HTTP mTLS sets CERT_REQUIRED and the client CA on uvicorn.Config."""
    from fastapi import FastAPI

    cert, key = write_self_signed(tmp_path)
    settings = Settings(
        http_insecure=False,
        http_tls_cert_file=cert,
        http_tls_key_file=key,
        http_tls_client_ca_file=cert,
        http_host="127.0.0.1",
        http_port=0,
    )
    ctx = build_http_ssl_context(
        Settings(http_insecure=False, http_tls_cert_file=cert, http_tls_key_file=key),
    )
    assert ctx is not None
    assert ctx.verify_mode != ssl.CERT_REQUIRED
    server = build_http_server(FastAPI(), settings)
    factory = server.config.ssl_context_factory
    assert factory is not None
    loaded = factory(server.config, lambda: ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER))
    assert loaded.verify_mode == ssl.CERT_REQUIRED
    assert loaded.minimum_version == ssl.TLSVersion.TLSv1_2


def test_rest_client_verify_accepts_ca_path(tmp_path: Path) -> None:
    """CA file paths are turned into an SSLContext for httpx."""
    from pixeldive_sdk.client import as_ssl_verify

    cert, _key = write_self_signed(tmp_path)
    ctx = as_ssl_verify(str(cert))
    assert isinstance(ctx, ssl.SSLContext)
    assert as_ssl_verify(True) is True


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
    with pytest.raises(RuntimeError, match="cert/key files are unset"):
        validate_auth_settings(
            Settings(
                environment="prod",
                auth_required=True,
                api_keys="alpha:tenant-a",
                http_insecure=False,
                grpc_insecure=False,
                grpc_tls_cert_file=Path("/certs/server.crt"),
                grpc_tls_key_file=Path("/certs/server.key"),
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
            f"127.0.0.1:{grpc_port}",
            token="alpha",
            insecure=False,
            root_certificates=pem,
            ssl_target_name_override="localhost",
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
        async with httpx.AsyncClient(verify=ssl.create_default_context(cafile=str(cert))) as client:
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
    """Plaintext probe uses HTTPConnection; TLS uses HTTPSConnection."""
    created: list[str] = []

    class FakeConn:
        def __init__(
            self, host: str, port: int, timeout: object = None, context: object = None
        ) -> None:
            del host, timeout, context
            self.port = port
            created.append(self.__class__.__name__)

        def request(self, method: str, path: str) -> None:
            del method, path

        def getresponse(self) -> object:
            return type("Resp", (), {"status": 200})()

        def close(self) -> None:
            return None

    class FakeHTTP(FakeConn):
        pass

    class FakeHTTPS(FakeConn):
        pass

    monkeypatch.setattr("app.ready_probe.http.client.HTTPConnection", FakeHTTP)
    monkeypatch.setattr("app.ready_probe.http.client.HTTPSConnection", FakeHTTPS)
    monkeypatch.setenv("HTTP_INSECURE", "true")
    monkeypatch.setenv("HTTP_PORT", "8000")
    probe()
    assert created == ["FakeHTTP"]
    monkeypatch.setenv("HTTP_INSECURE", "false")
    probe()
    assert created[-1] == "FakeHTTPS"


def test_ready_probe_rejects_http_error() -> None:
    """Non-success /ready status fails the HEALTHCHECK."""
    from app.ready_probe import get_ready

    class FakeConn:
        def request(self, method: str, path: str) -> None:
            del method, path

        def getresponse(self) -> object:
            return type("Resp", (), {"status": 503})()

        def close(self) -> None:
            return None

    with pytest.raises(OSError, match="503"):
        get_ready(FakeConn())  # type: ignore[arg-type]


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
    monkeypatch.setattr(
        "app.ready_probe.probe",
        lambda: (_ for _ in ()).throw(ValueError("bad port")),
    )
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 1


def test_ready_probe_rejects_bad_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-integer HTTP_PORT fails closed instead of crashing the probe."""
    from app.ready_probe import ready_port

    monkeypatch.setenv("HTTP_PORT", "not-a-port")
    with pytest.raises(ValueError):
        ready_port()


def test_ready_probe_loads_mtls_client_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """HEALTHCHECK presents a client cert when HTTP mTLS env is set."""
    cert, key = write_self_signed(tmp_path)
    monkeypatch.setenv("HTTP_TLS_CERT_FILE", str(cert))
    monkeypatch.setenv("HTTP_TLS_CLIENT_CERT_FILE", str(cert))
    monkeypatch.setenv("HTTP_TLS_CLIENT_KEY_FILE", str(key))
    https_context()
    monkeypatch.delenv("HTTP_TLS_CLIENT_KEY_FILE")
    with pytest.raises(ValueError, match="both"):
        https_context()


def test_grpc_client_rejects_pems_on_insecure_channel() -> None:
    """Passing TLS PEMs with insecure=True is a configuration error."""
    with pytest.raises(ValueError, match="insecure=False"):
        GrpcClient("127.0.0.1:1", insecure=True, root_certificates=b"ca")
