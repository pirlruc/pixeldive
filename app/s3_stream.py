"""Read an async S3 body in fixed-size windows."""

from collections.abc import AsyncIterator

from app.s3_types import S3Body


async def iter_body(body: S3Body, chunk_size: int) -> AsyncIterator[bytes]:
    """Yield ``chunk_size`` windows until the body is exhausted."""
    while True:
        chunk = await body.read(chunk_size)
        if not chunk:
            return
        yield chunk
