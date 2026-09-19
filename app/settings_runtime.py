"""HTTP, gRPC, auth, and list-limit settings mixed into Settings."""

from pathlib import Path


class RuntimeSettingsMixin:
    """Process bind addresses, upload ceilings, and credentials."""

    http_host: str = "0.0.0.0"
    http_port: int = 8000
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051
    max_image_bytes: int = 32 * 1024 * 1024
    max_batch_images: int = 100
    max_concurrent_saves: int = 8
    download_chunk_bytes: int = 64 * 1024
    list_default_limit: int = 50
    list_max_limit: int = 200
    auth_required: bool = False
    api_keys: str = ""
    grpc_insecure: bool = True
    grpc_tls_cert_file: Path | None = None
    grpc_tls_key_file: Path | None = None
    grpc_tls_client_ca_file: Path | None = None
    log_json: bool = True
