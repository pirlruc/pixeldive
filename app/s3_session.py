"""Build the unentered aiobotocore S3 client context."""

from typing import Any

from app.config import Settings


def s3_client_context(settings: Settings) -> Any:
    """Return ``create_client('s3', ...)`` without entering it."""
    from aiobotocore.session import get_session

    return get_session().create_client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
