"""Brief atheris harness for filename sanitizing and magic sniffing."""

import sys

import atheris

from app.blobs.filenames import sanitize_filename
from app.blobs.magic import matches_declared_type


def test_one_input(data: bytes) -> None:
    """Feed one input to both parsers. Crashes are the signal."""
    provider = atheris.FuzzedDataProvider(data)
    sanitize_filename(provider.ConsumeUnicodeNoSurrogates(80))
    header = provider.ConsumeBytes(16)
    declared = provider.ConsumeUnicodeNoSurrogates(40)
    matches_declared_type(declared, header)


def main() -> None:
    """Run a bounded fuzz session when -runs is passed, otherwise atheris defaults."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
