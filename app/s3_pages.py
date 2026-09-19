"""Page through S3 ``list_objects_v2`` responses."""

from collections.abc import AsyncIterator, Awaitable, Callable


async def iter_list_pages(
    list_page: Callable[[object | None], Awaitable[dict[str, object]]],
) -> AsyncIterator[dict[str, object]]:
    """Yield list pages until truncation stops or the continuation token is empty."""
    token: object | None = None
    while True:
        response = await list_page(token)
        yield response
        if not response.get("IsTruncated"):
            return
        token = response.get("NextContinuationToken")
        if not token:
            return
