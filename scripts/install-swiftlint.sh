#!/usr/bin/env bash
# Download a checksum-pinned SwiftLint binary into TMPDIR (SWIFT-LINT-001).
# Not a system OS install: the archive is unpacked under /tmp.
set -euo pipefail
VERSION="0.60.0"
WORKDIR="${TMPDIR:-/tmp}/pixeldive-swiftlint-${VERSION}"
mkdir -p "$WORKDIR"
OS="$(uname -s)"
ARCH="$(uname -m)"
if [[ "$OS" == Darwin ]]; then
  ARCHIVE="portable_swiftlint.zip"
  URL="https://github.com/realm/SwiftLint/releases/download/${VERSION}/${ARCHIVE}"
  SHA256="4c1f56c40a4b230e575aef096c95b82db76d63dd600697d489403586eb68cbb5"
elif [[ "$OS" == Linux && ( "$ARCH" == x86_64 || "$ARCH" == amd64 ) ]]; then
  ARCHIVE="swiftlint_linux_amd64.zip"
  URL="https://github.com/realm/SwiftLint/releases/download/${VERSION}/${ARCHIVE}"
  SHA256="65ff9a5c66351b5613311192559219b5ce30b0759990f39657ff29e08f68d92b"
else
  echo "no SwiftLint binary for ${OS}/${ARCH}" >&2
  exit 1
fi
if [[ ! -x "$WORKDIR/swiftlint" ]]; then
  curl -fsSL "$URL" -o "$WORKDIR/$ARCHIVE"
  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "$WORKDIR/$ARCHIVE" | awk '{print $1}')"
  else
    actual="$(shasum -a 256 "$WORKDIR/$ARCHIVE" | awk '{print $1}')"
  fi
  if [[ "$actual" != "$SHA256" ]]; then
    echo "SwiftLint checksum mismatch: got ${actual} expected ${SHA256}" >&2
    exit 1
  fi
  unzip -qo "$WORKDIR/$ARCHIVE" -d "$WORKDIR"
  chmod +x "$WORKDIR/swiftlint"
fi
echo "$WORKDIR/swiftlint"
