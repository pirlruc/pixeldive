"""Named limiter for blocking file work (APP-HTTP-001)."""

import anyio

blob_io = anyio.CapacityLimiter(4)
