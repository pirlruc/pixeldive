"""Call a named method on a lazily opened S3 client."""

from collections.abc import Awaitable, Callable
from typing import Any, cast


async def invoke(ensure: Callable[[], Awaitable[Any]], method: str, **kwargs: object) -> Any:
    """Await ``ensure()`` then ``getattr(client, method)(**kwargs)``."""
    client = await ensure()
    return cast(Any, await getattr(client, method)(**kwargs))
