"""Read an async S3 body in fixed-size windows."""

from collections.abc import AsyncIterator
from inspect import isawaitable

from app.blobs.s3_types import S3Body


async def close_body(body: object) -> None:
    """Close a get_object body if the client exposes close/aclose."""
    closer = getattr(body, "aclose", None) or getattr(body, "close", None)
    if closer is None:
        return
    result = closer()
    if isawaitable(result):
        await result


async def iter_body(body: S3Body, chunk_size: int) -> AsyncIterator[bytes]:
    """Yield ``chunk_size`` windows until the body is exhausted."""
    try:
        while True:
            chunk = await body.read(chunk_size)
            if not chunk:
                return
            yield chunk
    finally:
        await close_body(body)
