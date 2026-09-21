"""Cap consecutive empty upload chunks so a stream cannot stall forever."""

MAX_EMPTY_CHUNKS = 64


def empty_run_exceeded(run: int) -> bool:
    """True when ``run`` empty chunks in a row pass the stall cap."""
    return run > MAX_EMPTY_CHUNKS
