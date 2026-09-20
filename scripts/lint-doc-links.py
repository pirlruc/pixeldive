#!/usr/bin/env python3
"""Validate relative markdown and Cursor-rule links under the repository root.

Vendored from pirlruc/methodologies@1.2.1 via guardrails 1.6.0
(docs/guardrails/scripts/lint-doc-links.py). Refresh when bumping those pins.
Consuming-repo SKIP_DIR_NAMES also exclude .venv and test caches so a local
pip --target install cannot poison DOC-LINT-001.

Root resolution (first match wins): ``--root``, ``CONSUMING_REPO_ROOT``,
``git rev-parse --show-toplevel`` from the current working directory. A ``.git``
file whose contents start with ``gitdir:`` is a submodule boundary and is not
treated as the repo root, so a vendored copy of this script does not silently
lint the wrong tree.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
}
DOC_GLOBS = ("*.md", "*.mdc")
FENCE_OPEN = re.compile(r"^(`{3,}|~{3,})")
ABS_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")
REF_DEF = re.compile(r"^\s*\[[^\]]+\]:\s+(\S+)")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        help="Repository root to scan (overrides env and git detection)",
    )
    return parser.parse_args(argv)


def git_toplevel(cwd: Path) -> Path | None:
    """Return ``git rev-parse --show-toplevel`` for ``cwd``, or None."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    text = completed.stdout.strip()
    return Path(text).resolve() if text else None


def is_submodule_git(git_path: Path) -> bool:
    """Return True when ``.git`` is a gitdir pointer file (submodule/worktree)."""
    if not git_path.is_file():
        return False
    try:
        return git_path.read_text(encoding="utf-8").lstrip().startswith("gitdir:")
    except OSError:
        return False


def walk_repo_root(start: Path) -> Path | None:
    """Walk up from ``start``, skipping submodule checkouts."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        git_path = candidate / ".git"
        if not (candidate / "README.md").is_file() or not git_path.exists():
            continue
        if is_submodule_git(git_path):
            continue
        return candidate
    return None


def resolve_root(cli_root: Path | None) -> Path:
    """Resolve the invoking repository root."""
    if cli_root is not None:
        return cli_root.expanduser().resolve()
    env = os.environ.get("CONSUMING_REPO_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    cwd = Path.cwd()
    toplevel = git_toplevel(cwd)
    if toplevel is not None:
        return toplevel
    walked = walk_repo_root(cwd)
    if walked is not None:
        return walked
    return cwd.resolve()


def is_skipped(path: Path, root: Path) -> bool:
    """Return True when ``path`` sits under a skipped or nested-git directory."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    if any(part in SKIP_DIR_NAMES for part in rel.parts):
        return True
    current = path.parent
    while current != root and current != current.parent:
        if (current / ".git").exists():
            return True
        current = current.parent
    return False


def collect_doc_files(root: Path) -> list[Path]:
    """Return sorted markdown and Cursor-rule files under ``root``."""
    files: list[Path] = []
    for glob in DOC_GLOBS:
        files.extend(p for p in root.rglob(glob) if not is_skipped(p, root))
    return sorted(files)


def _fence_marker(line: str) -> str | None:
    """Return the fence marker on ``line``, or None."""
    match = FENCE_OPEN.match(line.lstrip())
    return match.group(1) if match else None


def _fence_step(line: str, fence: str | None) -> tuple[str | None, str]:
    """Advance fence state for one line; return (new_fence, emitted_text)."""
    marker = _fence_marker(line)
    blank = "\n" if line.endswith("\n") else ""
    if marker and fence is None:
        return marker, blank
    if marker and fence is not None and line.lstrip().startswith(fence):
        return None, blank
    return fence, (blank if fence is not None else line)


def strip_fences(text: str) -> str:
    """Blank out fenced code blocks so example links are not linted."""
    out: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        fence, piece = _fence_step(line, fence)
        out.append(piece)
    return "".join(out)


def strip_title(inner: str) -> str:
    """Drop an optional markdown link title from a destination."""
    text = inner.strip()
    if not text:
        return ""
    if text.startswith("<"):
        end = text.find(">")
        return text[1:end].strip() if end != -1 else text
    for quote in (' "', " '", " ("):
        idx = text.find(quote)
        if idx > 0:
            return text[:idx].strip()
    return text.split()[0]


def _read_angle_dest(text: str, start: int) -> tuple[str | None, int]:
    """Read a ``<destination>`` starting at ``start`` (the ``<``)."""
    end = text.find(">", start + 1)
    if end == -1:
        return None, start + 1
    close = text.find(")", end + 1)
    return text[start + 1 : end].strip(), (close + 1 if close != -1 else end + 1)


def _read_paren_dest(text: str, start: int) -> tuple[str | None, int]:
    """Read an unbracketed destination with nested parentheses."""
    depth = 1
    index = start
    while index < len(text):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return strip_title(text[start:index]), index + 1
        index += 1
    return None, start + 1


def read_inline_destination(text: str, start: int) -> tuple[str | None, int]:
    """Read the destination of a ``](`` link starting at ``start`` (after ``](``)."""
    index = start
    while index < len(text) and text[index] in " \t":
        index += 1
    if index >= len(text):
        return None, index
    if text[index] == "<":
        return _read_angle_dest(text, index)
    return _read_paren_dest(text, index)


def iter_destinations(text: str) -> list[str]:
    """Yield inline and reference-style markdown destinations."""
    dests: list[str] = []
    i = 0
    while True:
        start = text.find("](", i)
        if start == -1:
            break
        dest, nxt = read_inline_destination(text, start + 2)
        if dest:
            dests.append(dest)
        i = nxt
    for line in text.splitlines():
        match = REF_DEF.match(line)
        if match:
            dests.append(strip_title(match.group(1)))
    return dests


def path_from_destination(raw: str) -> str | None:
    """Return a relative filesystem path, or None when the dest is skipped."""
    link = unquote(raw.strip())
    if not link or link.startswith(ABS_PREFIXES):
        return None
    path_only = link.split("#", 1)[0].split("?", 1)[0].strip()
    return path_only or None


def is_repo_relative(path_only: str) -> bool:
    """Return True when ``path_only`` is not explicitly file-relative."""
    return not path_only.startswith(("./", "../")) and path_only not in {".", ".."}


def candidate_targets(source: Path, path_only: str, root: Path) -> list[Path]:
    """Return paths to try for a relative link (file-relative, then repo-root)."""
    targets = [source.parent / path_only]
    if is_repo_relative(path_only):
        targets.append(root / path_only)
    return targets


def target_ok(path: Path) -> bool:
    """Return True when ``path`` is a file, or a directory that contains README.md."""
    resolved = path.resolve()
    if resolved.is_file():
        return True
    return resolved.is_dir() and (resolved / "README.md").is_file()


def check_file(md_file: Path, root: Path) -> list[str]:
    """Return failure strings for one documentation file."""
    failures: list[str] = []
    text = strip_fences(md_file.read_text(encoding="utf-8"))
    rel = md_file.relative_to(root)
    for raw in iter_destinations(text):
        path_only = path_from_destination(raw)
        if path_only is None:
            continue
        if any(target_ok(candidate) for candidate in candidate_targets(md_file, path_only, root)):
            continue
        target = (md_file.parent / path_only).resolve()
        if is_repo_relative(path_only):
            target = (root / path_only).resolve()
        if target.is_dir():
            failures.append(f"{rel} -> {raw} (directory target; link a file)")
        else:
            failures.append(f"{rel} -> {raw}")
    return failures


def main(argv: list[str] | None = None) -> int:
    """Lint relative links; return 0 on success, 1 on failures."""
    args = parse_args(argv)
    root = resolve_root(args.root)
    doc_files = collect_doc_files(root)
    if not doc_files:
        print(f"ERROR: no markdown or Cursor-rule files found under {root}", file=sys.stderr)
        return 1
    failures: list[str] = []
    for md_file in doc_files:
        failures.extend(check_file(md_file, root))
    if failures:
        print("ERROR: Broken markdown links found:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Markdown link check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
