"""HTTP, gRPC, auth, and list-limit settings mixed into Settings."""

from pathlib import Path

from app.io_sizes import GRPC_UPLOAD_CHUNK_BYTES, IO_CHUNK_BYTES


class RuntimeSettingsMixin:
    """Process bind addresses, upload ceilings, and credentials."""

    http_host: str = "127.0.0.1"
    http_port: int = 8000
    grpc_host: str = "127.0.0.1"
    grpc_port: int = 50051
    max_image_bytes: int = 32 * 1024 * 1024
    max_batch_images: int = 100
    max_concurrent_saves: int = 8
    download_chunk_bytes: int = IO_CHUNK_BYTES
    list_default_limit: int = 50
    list_max_limit: int = 200
    auth_required: bool = False
    api_keys: str = ""
    http_insecure: bool = True
    grpc_insecure: bool = True
    tls_cert_file: Path | None = None
    tls_key_file: Path | None = None
    tls_client_ca_file: Path | None = None
    http_tls_cert_file: Path | None = None
    http_tls_key_file: Path | None = None
    http_tls_client_ca_file: Path | None = None
    grpc_tls_cert_file: Path | None = None
    grpc_tls_key_file: Path | None = None
    grpc_tls_client_ca_file: Path | None = None
    log_json: bool = True
    rate_limit_per_minute: int = 0
    rate_limit_window_seconds: float = 60.0
    tenant_max_upload_bytes: int = 0
    session_max_upload_bytes: int = 0
    orphan_sweep_interval_seconds: float = 0.0
    grpc_upload_chunk_bytes: int = GRPC_UPLOAD_CHUNK_BYTES
    environment: str = "development"
