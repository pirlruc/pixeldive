"""CLI entrypoint for the dual REST/gRPC server."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from app.runtime import run

__all__ = ["main", "run"]


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entrypoint used by Docker ENTRYPOINT and ``python main.py``."""
    del argv
    asyncio.run(run())


if __name__ == "__main__":
    main()
