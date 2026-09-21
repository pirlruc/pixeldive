"""gRPC aio transport for SessionService (API-001)."""

import grpc

from app.pb import session_service_pb2_grpc as pb_grpc
from app.rpc.grpc_errors import abort_rpc
from app.rpc.grpc_image_rpcs import ImageRpcMixin
from app.rpc.grpc_session_rpcs import SessionRpcMixin
from app.rpc.grpc_tls import build_grpc_server_credentials
from app.sessions.service import SessionService

# Re-export for tests that patch/import the abort helper.
_abort = abort_rpc


class SessionServicer(SessionRpcMixin, ImageRpcMixin, pb_grpc.SessionServiceServicer):
    """gRPC servicer that delegates to SessionService."""

    def __init__(self, service: SessionService) -> None:
        """Bind the shared business layer."""
        self._service = service


async def start_grpc_server(
    service: SessionService,
    host: str,
    port: int,
) -> tuple[grpc.aio.Server, int]:
    """Start an aio gRPC server and return it with the bound port."""
    ceiling = service._settings.max_image_bytes + (2 * 1024 * 1024)
    server = grpc.aio.server(
        options=[
            ("grpc.max_receive_message_length", ceiling),
            ("grpc.max_send_message_length", ceiling),
        ],
    )
    pb_grpc.add_SessionServiceServicer_to_server(SessionServicer(service), server)
    address = f"{host}:{port}"
    credentials = build_grpc_server_credentials(service._settings)
    if credentials is None:
        bound_port = server.add_insecure_port(address)
    else:
        bound_port = server.add_secure_port(address, credentials)
    await server.start()
    return server, bound_port
