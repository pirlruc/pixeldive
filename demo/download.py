"""Prime SDK downloads so upstream errors surface before StreamingResponse."""

from collections.abc import AsyncIterator

from pixeldive_sdk import RestClient


async def open_download(
    remote: RestClient,
    session_id: str,
    image_id: str,
) -> tuple[bytes, AsyncIterator[bytes]]:
    """Await the first chunk (and thus HTTP status) before returning the rest."""
    stream = remote.download_image(session_id, image_id)
    try:
        first = await anext(stream)
    except StopAsyncIteration:
        first = b""
    except BaseException:
        closer = getattr(stream, "aclose", None)
        if closer is not None:
            await closer()
        raise
    return first, stream


async def continue_download(first: bytes, stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    """Yield the primed first chunk then the remainder, always closing ``stream``."""
    try:
        yield first
        async for chunk in stream:
            yield chunk
    finally:
        aclose = getattr(stream, "aclose", None)
        if aclose is not None:
            await aclose()
