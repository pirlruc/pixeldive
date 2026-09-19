"""On-disk upload with a SHA-256 digest and byte count."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiofiles.os


@dataclass(frozen=True, slots=True)
class Spool:
    """Hashed spool file left by ``SpoolWriter``."""

    path: Path
    digest_hex: str
    size_bytes: int

    async def delete(self) -> None:
        """Remove the spool file if it is still present."""
        try:
            await aiofiles.os.remove(self.path)
        except FileNotFoundError:
            return
